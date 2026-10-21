"""Langchain 编排层（非 RAG）。

提供两类能力：
1) to_langchain_messages : 把工程内 {role, content} 消息列表转为 Langchain 消息对象。
2) run_itinerary_agent   : 行程规划 tool-calling 智能体。
   用 ChatOpenAI.bind_tools 强制调用 create_itinerary 工具，
   内置「空工具调用 → 强制重试一次」兜底（沿用旧工程稳健策略）。
"""
import json
import logging

from langchain_core.runnables import RunnableParallel, RunnableLambda, RunnablePassthrough

from services.langchain_layer.llm import get_chat_model
from services.langchain_layer.messages import to_langchain_messages
from services.langchain_layer.chains.context_chain import build_context_chain
from services.langchain_layer.chains.intent_chain import build_intent_chain
from services.langchain_layer.chains.router_chain import build_router_chain

logger = logging.getLogger(__name__)


# to_langchain_messages 已迁移至 services/langchain_layer/messages.py（供各 chain 复用）。
# 本模块保留 run_itinerary_agent 智能体逻辑（Phase 6 删除），并新增 build_chat_chain 顶层编排。


async def run_itinerary_agent(messages: list, tool_schema: dict,
                              *, temperature: float = 0.3,
                              model=None) -> dict:
    """行程规划 tool-calling 智能体。

    参数:
        messages    : 已经拼装好的消息列表（含 system + user 轮次，即 ai_service 的
                      messages_for_api），格式为 [{role, content}, ...]。
        tool_schema : OpenAI function-calling 风格的单个工具定义
                      （如 ITINERARY_TOOL 整体，或直接传其 function 体）。

    返回:
        {
          "tool_calls": [{"name", "args", "id", "type"}, ...],  # 可能为空列表
          "content": str,      # 模型文本（无工具调用时可用）
        }
        调用方负责：解析 args、做城市/天数/预算兜底、构造返回体。
    """
    # 兼容两种传参：ITINERARY_TOOL 整体（含 type/function）或直接传 function 体
    if tool_schema.get("type") == "function" and "function" in tool_schema:
        openai_tool = tool_schema
    else:
        openai_tool = {"type": "function", "function": tool_schema}

    if model is None:
        model = get_chat_model(temperature=temperature)
    model_with_tools = model.bind_tools([openai_tool], tool_choice="required")

    lc_messages = to_langchain_messages(messages)
    ai_msg = await model_with_tools.ainvoke(lc_messages)

    # 兜底：模型偶发未触发工具调用（限流/安全过滤/网络抖动）→ 强制重试一次
    if not getattr(ai_msg, "tool_calls", None):
        retry_note = HumanMessage(content=(
            "（系统补注：你上一轮未返回行程工具调用，请立即调用 create_itinerary 工具"
            "返回完整行程方案，不要输出纯文本或 JSON 对象。）"
        ))
        ai_msg = await model_with_tools.ainvoke(lc_messages + [retry_note])

    tool_calls = []
    for tc in getattr(ai_msg, "tool_calls", None) or []:
        tool_calls.append({
            "name": tc.get("name"),
            "args": tc.get("args"),
            "id": tc.get("id"),
            "type": tc.get("type", "function"),
        })
    return {"tool_calls": tool_calls, "content": ai_msg.content or ""}


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
    if intent_chain is None:
        intent_chain = build_intent_chain(model=model)
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
        is_plan_det = raw.get("is_plan_det", False)
        is_weather_det = raw.get("is_weather_det", False)

        # 合并意图：确定性硬守门 + LLM 分类（plan 优先，避免天气/规划冲突）
        is_plan = bool(is_plan_det or intent.get("is_plan"))
        is_weather = bool(is_weather_det or intent.get("is_weather"))
        if is_plan:
            is_weather = False

        # 拼装消息（委托 ai_service 抽取的静态方法，含 M1 城市修复）
        from services.ai_service import AIService
        messages = AIService._assemble_messages(
            message, history_messages, weather_prompt, cities, days, budget, is_plan
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

    return (
        RunnableParallel({
            "context": context_chain,
            "intent": intent_chain,
            "raw": RunnablePassthrough(),
        })
        | RunnableLambda(_assemble)
        | router_chain
        | RunnableLambda(_postprocess)
    )
