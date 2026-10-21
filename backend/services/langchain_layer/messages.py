"""Langchain 消息格式转换（从 orchestrator 抽出，作为链层公共原语）。

仅负责工程内 {role, content} 消息列表 ↔ Langchain BaseMessage 对象的互转，
供各 chain 复用；不含任何业务/工具逻辑。
"""
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)


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
