"""纯 Langchain 编排层 · 问答链与智能体

检索层现在就是 Langchain PGVector 的 retriever（见 services/rag/vector_store.py），
编排层只负责把「检索 → 拼上下文 → LLM → 解析」串成一条可调用链，不再有 LlamaIndex 桥接。

- build_qa_chain：用 LCEL 构建 RAG 问答链，retriever 直接来自 PGVector。
- build_agent（进阶）：tool-calling 智能体，工具含「景点检索」「天气查询」，演示 Langchain 的意图编排。
"""

from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import tool

from services.langchain_layer.llm import get_deepseek_llm


# doc_type → 中文标签，便于在上下文里标明资料类型
DOC_TYPE_LABEL = {
    "scenic_spot": "景点",
    "city": "城市知识",
    "guide": "深度攻略",
    "topic": "主题专题",
    "itinerary": "行程模板",
    "faq": "常见问题",
}


def _format_docs(docs: List[Document]) -> str:
    """把召回的 Document 列表拼成一段上下文字符串，喂给 LLM。

    兼容两类语料：scenic_spot（用 name）与 knowledge_doc（用 title），
    并标注 doc_type 中文标签，帮助 LLM 区分「景点 / 城市知识 / 攻略 / 行程模板 / FAQ」。
    """
    if not docs:
        return "（未检索到相关知识）"
    blocks = []
    for i, d in enumerate(docs, 1):
        meta = d.metadata or {}
        title = meta.get("title") or meta.get("name") or f"资料{i}"
        dt = meta.get("doc_type", "")
        label = DOC_TYPE_LABEL.get(dt, dt or "资料")
        city = meta.get("city") or ""
        head = f"【资料{i}｜{label}】{title}" + (f"（{city}）" if city else "")
        blocks.append(head + "\n" + d.page_content)
    return "\n\n".join(blocks)


def build_qa_chain(retriever: BaseRetriever, llm=None):
    """构建 RAG 问答链，返回可直接 chain.invoke(question) 的 Runnable。

    retriever 是 Langchain PGVector 的 retriever（可带 city 过滤）。
    """
    llm = llm or get_deepseek_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你是专业的旅游助手。下面【检索到的资料】可能包含多种类型："
         "景点本体、城市知识、深度攻略、主题专题、行程模板、常见问题。"
         "请严格【只使用】检索资料中的信息来回答，不要编造未出现的事实；"
         "信息不足时直接说不知道。\n"
         "当用户问行程规划 / 玩法 / 城市概况时，优先结合「行程模板 / 城市知识 / 深度攻略」"
         "组织回答，并可在合适处引用资料中出现的具体景点名称；"
         "问具体景点时以「景点」类资料为准。回答用自然、有条理的中文，可适当分点。"),
        ("human",
         "【检索到的资料】\n{context}\n\n【用户问题】\n{question}"),
    ])
    # LCEL 管道：先并行算出 context（检索+拼接）与 question（透传），再进 prompt→LLM→解析
    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


# ===================== 进阶：Langchain 智能体（意图编排） =====================

def build_agent(retriever: BaseRetriever, llm=None, weather_service=None):
    """tool-calling 智能体：根据用户问题自动决定调用「景点检索」还是「天气查询」。

    注意：
      - 此处 retriever 直接来自 PGVector，不再依赖任何 LlamaIndex 对象。
      - Langchain 1.x 的 agent API 已改为 ``create_agent``，返回 CompiledStateGraph；
        调用方式：``agent.invoke({"messages": [("human", "用户问题")]})``。
    """
    from langchain.agents import create_agent

    @tool
    def scenic_search(query: str) -> str:
        """在景点知识库中检索与 query 相关的景点信息（城市可在 query 中指明）。"""
        docs = retriever.invoke(query)
        return _format_docs(docs)

    @tool
    def get_weather(city: str) -> str:
        """查询指定城市的天气预报。"""
        if weather_service is None:
            return "（未配置天气服务）"
        import asyncio
        try:
            data = asyncio.run(weather_service.get_weather_forecast(city, days=3))
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                loop = asyncio.get_event_loop()
                data = loop.run_until_complete(weather_service.get_weather_forecast(city, days=3))
            else:
                raise
        return (weather_service.format_weather_for_prompt(data)
                if data.get("success") else "天气查询失败")

    tools = [scenic_search, get_weather]
    llm = llm or get_deepseek_llm()
    agent = create_agent(
        llm,
        tools,
        system_prompt="你是旅游助手，按需调用工具获取景点或天气信息后再回答。",
    )
    return agent
