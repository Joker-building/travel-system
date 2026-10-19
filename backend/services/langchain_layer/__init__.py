"""Langchain 编排层（纯 Langchain 实现）

- llm.py：DeepSeek（兼容 OpenAI 协议）的 ChatOpenAI 封装。
- orchestrator.py：RAG 问答链（LCEL）与 tool-calling 智能体。
- 检索后端由 services/rag/vector_store.py 提供（PGVector retriever）。
"""

__all__ = ["llm", "orchestrator"]
