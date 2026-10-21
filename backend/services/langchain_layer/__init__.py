"""Langchain 接入层（非 RAG）。

本包只承载「LLM 接入 + 编排」，不含任何向量检索 / 知识库逻辑：
- llm.py          : DeepSeek 的 ChatOpenAI 封装（OpenAI 兼容接入层）
- messages.py     : {role, content} → Langchain 消息对象列表
- orchestrator.py : 顶层对话链 build_chat_chain（LCEL 多链 + 嵌套 + 并发）
- chains/         : 子链（context / intent / router / plan / qa / weather / scenic_*）

对外暴露的核心 API（各子模块符号在此 re-export，调用方统一从本包导入）：
- get_chat_model         : 构造对接 DeepSeek 的 ChatOpenAI 实例
- to_langchain_messages  : [{role, content}] → Langchain 消息对象列表
"""
from services.langchain_layer.llm import get_chat_model
from services.langchain_layer.messages import to_langchain_messages

__all__ = [
    "get_chat_model",
    "to_langchain_messages",
]
