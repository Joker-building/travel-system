"""Langchain 编排层（非 RAG）。

顶层对话编排（build_chat_chain）：
    LCEL 多链 + 嵌套 + 并发的顶层对话链。
    拓扑：RunnableParallel({context, intent, raw}) | _assemble | router_chain | _postprocess
      - context_chain   并发加载天气（history/prefs 预留扩展）；
      - intent_chain    LLM 意图分类（plan>weather>qa，异常降级 qa）；
      - router_chain    RunnableBranch 按意图路由到 plan_chain / qa_chain（链内嵌链）；
      - _postprocess    统一输出 {response_type, data, error_code}（M8）。
    意图合并采用「确定性硬守门 + LLM 分类」双轨：is_plan = is_plan_det or intent.is_plan，
    plan 优先以消解天气/规划冲突（M1）。

底层工具（to_langchain_messages / get_chat_model）位于 messages.py / llm.py，供各 chain 复用。
"""
import logging

from langchain_core.runnables import RunnableParallel, RunnableLambda, RunnablePassthrough

from services.langchain_layer.chains.context_chain import build_context_chain
from services.langchain_layer.chains.intent_chain import build_intent_chain
from services.langchain_layer.chains.router_chain import build_router_chain

logger = logging.getLogger(__name__)


def build_chat_chain(*, history_loader=None, prefs_loader=None, weather_service=None,
                     plan_tools=None, model=None, intent_chain=None, router_chain=None):
    """构建顶层对话链（多链 + 嵌套 + 并发，对应方案 3.1）。

    拓扑（chain 内嵌 chain + RunnableParallel 并发）：
        RunnableParallel({
            "context": context_chain,   # 并发加载 weather（history/prefs 预留扩展）
            "intent":  intent_chain,   # LLM 意图分类
            "raw":     RunnablePassthrough(),  # 保留原始输入
        })
        | _assemble        # 拼装 system prompt + 天气注入 + 历史自适应（含 M1 城市修复）
        | router_chain     # RunnableBranch 按意图路由（chain 内嵌 chain）
        | _postprocess     # M8 统一输出 {response_type, data, error_code}

    输入契约（由 AIService.chat 在链外算好并传入，遵守 M7）：
        {
          "message": str,
          "history": [ChatMessage|{role,content}, ...],  # 链外查好的历史
          "weather": {"city": str, "days": int},         # 给 context.weather_chain
          "prefs":   {...},                                # 给 context.prefs_loader
          "cities":  [str],                                # 确定性提取（M1 统一算一次）
          "days":    int|None,
          "budget":  int|None,
          "is_plan_det": bool,                             # 确定性 plan 硬守门
          "is_weather_det": bool,                          # 确定性 weather 硬守门
        }

    输出（M8 统一）：
        {"response_type": "itinerary"|"question_answer",
         "data": <解析后的行程 dict 或 QA dict>,
         "error_code": None | "EMPTY_PLAN" | ...}

    intent_chain / router_chain：可注入已构建的子链（便于单测分别注入不同模型），
        缺省则现场用 model 构建。
    """
    if plan_tools is None:
        # 延迟取 ITINERARY_TOOL，避免模块级循环导入
        from services.ai_service import ITINERARY_TOOL
        plan_tools = [ITINERARY_TOOL]

    context_chain = build_context_chain(
        history_loader=history_loader, prefs_loader=prefs_loader, weather_service=weather_service
    )
    # intent_chain 可空：为空时由 chat() 在链外算好的 is_plan_det/is_weather_det 直接守门（M7）。
    # 非空时（如单测）仍作 LLM 分类 OR 加固。
    if router_chain is None:
        router_chain = build_router_chain(tools=plan_tools, model=model)

    def _assemble(inputs: dict) -> dict:
        context = inputs.get("context") or {}
        intent = inputs.get("intent") or {}
        raw = inputs.get("raw") or {}
        message = raw.get("message", "")
        history_messages = raw.get("history") or []
        weather_prompt = (context.get("weather") or {}).get("prompt", "")
        cities = raw.get("cities") or []
        days = raw.get("days")
        budget = raw.get("budget")
        summary = raw.get("summary") or None
        is_plan_det = raw.get("is_plan_det", False)
        is_weather_det = raw.get("is_weather_det", False)

        # 合并意图：注入了 intent_chain 时 LLM 分类作 OR 加固；否则直接信任确定性守门（M7）。
        is_plan = bool(is_plan_det or intent.get("is_plan"))
        is_weather = bool(is_weather_det or intent.get("is_weather"))
        if is_plan:
            is_weather = False

        # 拼装消息（委托 ai_service 抽取的静态方法，含 M1 城市修复 + 摘要注入）
        from services.ai_service import AIService
        messages = AIService._assemble_messages(
            message, history_messages, weather_prompt, cities, days, budget, is_plan, summary=summary
        )
        return {"messages": messages, "is_plan": is_plan, "is_weather": is_weather}

    def _postprocess(output) -> dict:
        # output 是 router 分支链的产物。
        # plan 分支：plan_chain 产出 tool_calls —— 约定为 list[{name,args,id,type}]，
        #           （亦兼容 {"tool_calls":[...]} 字典形态，便于旧契约过渡）。
        # qa 分支：产出归一化 QA dict（非 list、无 tool_calls 键）。
        if isinstance(output, list):
            tool_calls = output
        elif isinstance(output, dict) and "tool_calls" in output:
            tool_calls = output.get("tool_calls") or []
        else:
            # QA 分支
            return {"response_type": "question_answer", "data": output, "error_code": None}

        if not tool_calls:
            return {"response_type": "itinerary", "data": {}, "error_code": "EMPTY_PLAN"}
        from services.ai_service import AIService
        args = AIService._extract_tool_args(tool_calls[0].get("args"))
        return {"response_type": "itinerary", "data": args, "error_code": None}

    parallel = {
        "context": context_chain,
        "raw": RunnablePassthrough(),
    }
    if intent_chain is not None:
        parallel["intent"] = intent_chain
    return (
        RunnableParallel(parallel)
        | RunnableLambda(_assemble)
        | router_chain
        | RunnableLambda(_postprocess)
    )
