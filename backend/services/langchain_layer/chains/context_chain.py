"""上下文加载链（RunnableParallel 并发：history + weather + prefs）。

对应方案 3.2，并修复 M4（chat() 职责过载）—— 把「加载上下文」抽成一条并发链。

三条子链由 RunnableParallel 异步并发执行：
- history : 会话历史（含截断 / 自适应），由注入的 history_loader 获取
- weather : 天气（复用 weather_chain，失败降级不阻断主链）
- prefs   : 用户偏好（可空），由注入的 prefs_loader 获取

输入契约:
    {
      "history": {<history 子输入>},          # 透传给 history_loader
      "weather": {"city": str, "days": int},  # 透传给 weather_chain
      "prefs":   {<prefs 子输入>},            # 透传给 prefs_loader
    }
输出:
    {
      "history": {...},
      "weather": {"success": bool, "prompt": str},
      "prefs":   {...},
    }

并发约束（M7）：链内不执行 DB 写；history / prefs 的 loader 由调用方
（AIService.chat）注入 —— 可传「链外已查好的数据」或安全的同步 / 异步查询函数。
链内只做无状态 LLM / 计算 / 外部 API 调用（weather 是无状态 API 调用，天然可并发）。

chain 内嵌 chain：weather 分支用 `RunnableLambda(_extract_weather) | weather_chain`
把子输入取出后再管道到下一条链，正是用户要求的「chain 里面包着 chain」。
"""
import logging

from langchain_core.runnables import RunnableLambda, RunnableParallel

from services.langchain_layer.chains.weather_chain import build_weather_chain

logger = logging.getLogger(__name__)


def build_context_loader(name: str, loader):
    """构造一个上下文子链（RunnableLambda 包装 loader），供 history / prefs 复用。

    loader: 同步或 async 可调用，签名 (inputs: dict) -> dict，
            返回该维度上下文 dict。异常由本函数兜底包裹为 {}（降级，不阻断主链）。

    name: 仅用于日志标识。
    """
    async def _run(inputs: dict) -> dict:
        try:
            result = loader(inputs)
            # 兼容 loader 返回协程（async 函数）的情况
            if hasattr(result, "__await__"):
                result = await result
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.warning("context_loader[%s] 失败降级: %s", name, e)
            return {}
    return RunnableLambda(_run)


def _extract_weather(inputs: dict) -> dict:
    """从顶层输入取出 weather 子输入，再管道给 weather_chain（chain 内嵌 chain）。"""
    return inputs.get("weather", {}) or {}


def build_context_chain(*, history_loader=None, prefs_loader=None, weather_service=None):
    """构建并发上下文加载链。

    history_loader / prefs_loader: 可注入的 (inputs: dict) -> dict 函数（同步或 async）。
        默认返回 {}（便于单测与降级）。Phase 4 整合时，
        AIService.chat 注入真实的「历史 / 偏好查询」逻辑（链外查 DB，遵守 M7）。
    weather_service: 透传给 build_weather_chain（可注入，便于单测）。

    三个分支通过 RunnableParallel 异步并发（Langchain 原生 asyncio.gather）。
    """
    history_loader = history_loader or (lambda _inputs: {})
    prefs_loader = prefs_loader or (lambda _inputs: {})

    weather_chain = build_weather_chain(weather_service=weather_service)

    return RunnableParallel({
        # history / prefs 子链：从顶层输入取各自子字段，再交给注入的 loader
        "history": build_context_loader(
            "history", lambda i: history_loader(i.get("history", {}))
        ),
        # weather 子链：取出子输入后管道给 weather_chain（chain 内嵌 chain）
        "weather": RunnableLambda(_extract_weather) | weather_chain,
        "prefs": build_context_loader(
            "prefs", lambda i: prefs_loader(i.get("prefs", {}))
        ),
    })
