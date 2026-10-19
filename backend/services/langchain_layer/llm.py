"""DeepSeek 模型封装（Langchain 接入层）。

仅作为 LLM 接入层使用——不含任何 RAG / 向量检索逻辑。
业务侧通过 get_chat_model() 拿到一个配置好的 ChatOpenAI 实例，
密钥与模型名从 config.settings 注入，无需直接 import langchain。
"""
from langchain_openai import ChatOpenAI

from config import settings


def _deepseek_base_url() -> str:
    """从 DEEPSEEK_API_URL 推导 Langchain 所需的 base_url。

    DEEPSEEK_API_URL 形如 https://api.deepseek.com/v1/chat/completions，
    ChatOpenAI 会在 base_url 之后拼接 /chat/completions，
    因此这里去掉该后缀，得到 https://api.deepseek.com/v1。
    """
    url = settings.DEEPSEEK_API_URL or ""
    return url.replace("/chat/completions", "").rstrip("/")


def get_chat_model(*, temperature: float = 0.3, max_tokens: int = 8192,
                  timeout: float = 120.0, **kwargs) -> ChatOpenAI:
    """构造对接 DeepSeek 的 ChatOpenAI 实例。

    参数通过 settings 注入（DEEPSEEK_API_KEY / DEEPSEEK_MODEL / base_url），
    业务侧无需关心密钥，也无需直接 import langchain。
    """
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=_deepseek_base_url(),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs,
    )
