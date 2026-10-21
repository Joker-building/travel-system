"""Phase 1 基础设施单测（TDD）：链工厂 + 消息转换，使用 fake model 避免真实 LLM 调用。"""
import pytest
from langchain_core.runnables import Runnable
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langchain_core.language_models.fake_chat_models import FakeListChatModel, GenericFakeChatModel


class FakeToolModel(GenericFakeChatModel):
    """测试用 fake：覆盖 bind_tools 返回自身，使 tool-calling 链可在不调真实 LLM 下构造与运行。"""
    def bind_tools(self, tools, **kwargs):
        return self

from services.langchain_layer.messages import to_langchain_messages
from services.langchain_layer.chains.base import (
    build_json_chain,
    build_tool_chain,
    _parse_tool_calls,
)


# ---- to_langchain_messages（迁移无回归） ----
def test_to_langchain_messages_roles():
    msgs = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "a"},
        {"role": "tool", "content": "t", "tool_call_id": "1"},
        {"role": "unknown", "content": "x"},
    ]
    out = to_langchain_messages(msgs)
    assert len(out) == 5
    assert isinstance(out[0], SystemMessage)
    assert isinstance(out[1], HumanMessage)
    assert isinstance(out[2], AIMessage)
    assert isinstance(out[3], ToolMessage)
    assert isinstance(out[4], HumanMessage)


def test_to_langchain_messages_none_content():
    out = to_langchain_messages([{"role": "user", "content": None}])
    assert out[0].content == ""


# ---- build_json_chain ----
def test_build_json_chain_returns_runnable():
    fake = FakeListChatModel(responses=['{"ok": true}'])
    chain = build_json_chain("sys", model=fake)
    assert isinstance(chain, Runnable)


def test_build_json_chain_parses():
    fake = FakeListChatModel(responses=['{"ok": true}'])
    chain = build_json_chain("sys", model=fake)
    assert chain.invoke({"input": "hi"}) == {"ok": True}


# ---- build_tool_chain ----
def test_build_tool_chain_returns_runnable():
    fake = FakeToolModel(messages=iter([AIMessage(content="x")]))
    chain = build_tool_chain(
        "sys", [{"type": "function", "function": {"name": "f", "parameters": {}}}],
        model=fake,
    )
    assert isinstance(chain, Runnable)


def test_build_tool_chain_parses_tool_calls():
    fake = FakeToolModel(messages=iter([AIMessage(
        content="x",
        tool_calls=[{"name": "f", "args": {"a": 1}, "id": "1", "type": "tool_call"}],
    )]))
    chain = build_tool_chain(
        "sys", [{"type": "function", "function": {"name": "f", "parameters": {}}}],
        model=fake,
    )
    out = chain.invoke({"input": "hi"})
    assert isinstance(out, list) and out[0]["name"] == "f"
    assert out[0]["args"] == {"a": 1}


# ---- _parse_tool_calls ----
def test_parse_tool_calls_empty():
    class M:
        tool_calls = None
    assert _parse_tool_calls(M()) == []


def test_parse_tool_calls_normal():
    class M:
        tool_calls = [{"name": "f", "args": {"a": 1}, "id": "1"}]
    out = _parse_tool_calls(M())
    assert out[0]["name"] == "f" and out[0]["args"] == {"a": 1}
