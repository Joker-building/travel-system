"""Phase 2 链单测用的假模型 / 假服务（零真实 LLM / 零网络调用）。

- SeqChatModel : 可编排「按调用次序返回不同响应」的假 ChatModel，
  支持 content（JSON 文本）与 tool_calls 两种形态，且兼容 bind / bind_tools /
  bind_response_format（链式 bind 仍共享底层实例状态，便于验证 with_fallbacks 重试）。
- FakeWeatherService : 可注入 weather_chain 的假天气服务（成功 / 失败两种构造）。
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class SeqChatModel(BaseChatModel):
    """按 responses 列表顺序返回 AIMessage 的假模型。

    responses: list[dict]，每个 dict 形如
        {"content": "<json 文本或空串>", "tool_calls": [{"name","args","id","type"}]}
    调用第 n 次返回 responses[min(n, len-1)]，便于模拟「主链空 → 重试成功」。
    bind / bind_tools / bind_response_format 均返回自身（共享状态），
    因此 with_fallbacks 的兜底链复用到同一底层实例，调用计数连续。
    """

    responses: list = []
    _i: int = 0

    @property
    def _llm_type(self) -> str:
        return "seq-chat-fake"

    def bind(self, **kwargs):
        return self

    def bind_tools(self, tools=None, **kwargs):
        self._tools = tools
        return self

    def bind_response_format(self, **kwargs):
        return self

    def _make_message(self, resp: dict) -> AIMessage:
        return AIMessage(
            content=resp.get("content", ""),
            tool_calls=resp.get("tool_calls", []) or [],
        )

    def _generate(self, messages, **kwargs) -> ChatResult:
        idx = min(self._i, len(self.responses) - 1) if self.responses else 0
        self._i += 1
        msg = self._make_message(self.responses[idx] if self.responses else {})
        return ChatResult(generations=[ChatGeneration(message=msg)])

    async def _agenerate(self, messages, **kwargs) -> ChatResult:
        return self._generate(messages, **kwargs)


class FakeWeatherService:
    """可注入 weather_chain 的假天气服务。

    success=True 时返回预置 prompt；fail=True 时 get_weather_forecast 抛异常，
    用于验证降级（success=False 且不向上抛）。
    """

    def __init__(self, prompt: str = "[WEATHER]", fail: bool = False):
        self._prompt = prompt
        self._fail = fail

    async def get_weather_forecast(self, city, days=3):
        if self._fail:
            raise RuntimeError("mock weather failure")
        return {"success": True, "city": city, "days": days}

    def format_weather_for_prompt(self, data) -> str:
        if self._fail:
            return ""
        return f"{self._prompt}:{data.get('city')}"
