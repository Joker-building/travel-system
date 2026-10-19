"""RAG 检索层（纯 Langchain + pgvector 实现）

本包只负责把景点知识库做成可语义检索的向量索引，对外暴露 vector_store。
编排逻辑在 services/langchain_layer/，负责「检索 → 拼上下文 → LLM → 解析」。
"""

__all__ = ["vector_store"]
