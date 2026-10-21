"""天气获取链（RunnableLambda 包装 WeatherService，可失败降级）。

输入:  {"city": str, "days": int}
输出:  {"success": bool, "prompt": str}
- success=True  : prompt 为已格式化的「注入式」天气文本块，可直接拼进 system prompt。
- success=False : 获取失败（异常/接口不可用），prompt 为空，主链可继续（不阻断）。

设计要点（修复 M3 可观测 + 三级降级延续）：
- 全程 try/except，异常仅记 warning 日志并返回 success=False，绝不向上抛，
  保证天气缺失时聊天/规划主流程不中断（与旧工程「天气三级降级」语义一致）。
- 通过 weather_service 注入便于单测；默认懒加载真实 WeatherService。
"""
import logging

from langchain_core.runnables import RunnableLambda

logger = logging.getLogger(__name__)


def build_weather_chain(weather_service=None):
    """构建天气获取链。

    weather_service: 可选注入，需提供 async get_weather_forecast(city, days) 与
                    format_weather_for_prompt(data) 两个方法；为 None 时懒加载
                    真实 WeatherService（需联网/本地数据）。
    """

    async def _fetch(inputs: dict) -> dict:
        city = inputs.get("city")
        days = inputs.get("days", 3)
        if not city:
            return {"success": False, "prompt": ""}
        try:
            svc = weather_service
            if svc is None:
                from services.weather_service import WeatherService
                svc = WeatherService()
            data = await svc.get_weather_forecast(city, days=days)
            if data.get("success"):
                prompt = svc.format_weather_for_prompt(data)
                return {"success": True, "prompt": prompt or ""}
            logger.warning("weather_chain: 天气接口返回未成功 city=%s data=%s",
                           city, str(data)[:200])
            return {"success": False, "prompt": ""}
        except Exception as e:  # 任何异常都降级，不阻断主链
            logger.warning("weather_chain 降级: %s", e)
            return {"success": False, "prompt": ""}

    return RunnableLambda(_fetch)
