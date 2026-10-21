"""行程规划链（plan_chain）：tool-calling 强制调用 create_itinerary + 空调用重试。

输入:  {"messages": [{role, content}, ...]}
输出:  {"tool_calls": [{"name", "args", "id", "type"}, ...], "content": str}

要点（延续旧 run_itinerary_agent 稳健策略，修复 M3 可观测）：
- 主链：messages → model.bind_tools(tools, tool_choice="required") → 解析 tool_calls。
- 空调用兜底：模型偶发未触发工具调用时抛 _NoToolCallError，
  经 with_fallbacks 触发重试链（追加补注，强制要求调用工具一次）。
- tools 必须由调用方显式传入（如 ITINERARY_TOOL），保持链与业务解耦。
- 注意：M1（多城市 dest_city 取错）的修复在 orchestrator 阶段统一计算 primary_city 后注入，
  本链只负责「调用 → 解析 → 重试」，不重复做城市兜底。
"""
import logging

from langchain_core.runnables import RunnableLambda

from services.langchain_layer.llm import get_chat_model
from services.langchain_layer.messages import to_langchain_messages
from services.langchain_layer.chains.base import _parse_tool_calls

logger = logging.getLogger(__name__)


class _NoToolCallError(Exception):
    """规划模型未返回任何 tool_calls 时抛出，用于触发 with_fallbacks 重试。"""


# 空工具调用重试补注：强制要求立即调用 create_itinerary。
_PLAN_RETRY_NOTE = {
    "role": "user",
    "content": (
        "（系统补注：你上一轮未返回行程工具调用，请立即调用 create_itinerary 工具"
        "返回完整行程方案，不要输出纯文本或 JSON 对象。）"
    ),
}


def _tool_chain_for(model, tools, tool_choice="required"):
    model_with_tools = model.bind_tools(tools, tool_choice=tool_choice)
    return RunnableLambda(lambda inputs: to_langchain_messages(inputs["messages"])) | model_with_tools | RunnableLambda(_parse_tool_calls)


def _require_tools(parsed: list) -> list:
    if not parsed:
        raise _NoToolCallError("规划模型未返回 tool_calls")
    return parsed


def build_plan_chain(model=None, *, tools: list, tool_choice: str = "required",
                    temperature: float = 0.3):
    """构建行程规划链（含空调用重试兜底）。

    tools: 必填，OpenAI function-calling 风格的工具定义列表（如 [ITINERARY_TOOL]）。
    model: 可注入（单测用 SeqChatModel），默认真实 DeepSeek。
    """
    if model is None:
        model = get_chat_model(temperature=temperature)

    primary = _tool_chain_for(model, tools, tool_choice) | RunnableLambda(_require_tools)

    async def _retry(inputs: dict) -> list:
        retry_messages = inputs["messages"] + [_PLAN_RETRY_NOTE]
        return await (_tool_chain_for(model, tools, tool_choice) | RunnableLambda(_require_tools)).ainvoke(
            {"messages": retry_messages}
        )

    return primary.with_fallbacks([RunnableLambda(_retry)])
