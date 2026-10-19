"""Langchain 编排层（非 RAG）。

提供两类能力：
1) to_langchain_messages : 把工程内 {role, content} 消息列表转为 Langchain 消息对象。
2) run_itinerary_agent   : 行程规划 tool-calling 智能体。
   用 ChatOpenAI.bind_tools 强制调用 create_itinerary 工具，
   内置「空工具调用 → 强制重试一次」兜底（沿用旧工程稳健策略）。
"""
import json

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from services.langchain_layer.llm import get_chat_model


def to_langchain_messages(messages: list) -> list:
    """将 [{role, content}, ...] 转换为 Langchain BaseMessage 列表。

    支持 system / user / assistant / tool 四种角色；
    对 None 内容做空串兜底，避免部分模型不接受 null content。
    """
    lc_messages = []
    for m in messages or []:
        role = (m.get("role") or "").lower()
        content = m.get("content")
        if content is None:
            content = ""
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            # 仅文本助手消息（历史 QA 落库为自然语言，不含 tool_calls）
            lc_messages.append(AIMessage(content=content))
        elif role == "tool":
            lc_messages.append(
                ToolMessage(content=content, tool_call_id=m.get("tool_call_id", ""))
            )
        else:
            # 未知角色按 user 处理，保证不丢消息
            lc_messages.append(HumanMessage(content=content))
    return lc_messages


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
