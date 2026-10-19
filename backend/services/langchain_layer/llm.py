"""Langchain 编排层 · LLM 封装

DeepSeek 兼容 OpenAI 协议，因此用 langchain-openai 的 ChatOpenAI 接入即可。
编排层（链 / 智能体）统一从这里拿 LLM，避免到处硬编码 base_url。
"""

from langchain_openai import ChatOpenAI
from config import settings


def get_deepseek_llm(temperature: float = 0.3, max_tokens: int = 2048) -> ChatOpenAI:
    """返回接入 DeepSeek 的 Langchain 聊天模型。"""
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,            # 默认 "deepseek-chat"
        api_key=settings.DEEPSEEK_API_KEY,
        # OpenAI 客户端会自动拼 /chat/completions，所以 base_url 填到 /v1 即可
        base_url="https://api.deepseek.com/v1",
        temperature=temperature,
        max_tokens=max_tokens,
    )
