"""understand_chain 单测：LLM 优先抽取意图+实体，异常降级规则，上下文继承。

全部零真实 LLM（用 SeqChatModel 注入固定 JSON）。
"""
import asyncio
import json

from services.langchain_layer.chains.understand_chain import build_understand_chain
from tests.chain_fakes import SeqChatModel


def _json_model(obj):
    return SeqChatModel(responses=[{
        "content": json.dumps(obj, ensure_ascii=False),
        "tool_calls": [],
    }])


def test_understand_plan_with_entities():
    """plan + 城市/天数/预算 抽取。"""
    m = _json_model({"intent": "plan", "cities": ["三亚"], "days": 5,
                    "budget": 3000, "weather_city": None,
                    "is_continuation": False, "confidence": 0.95})
    out = asyncio.run(build_understand_chain(model=m).ainvoke(
        {"message": "规划三亚5日游预算3000", "history": []}))
    assert out.intent == "plan"
    assert out.cities == ["三亚"]
    assert out.days == 5
    assert out.budget == 3000


def test_understand_weather_city_outside_whitelist():
    """天气分支点名白名单外城市（鸡西）正确抽取。"""
    m = _json_model({"intent": "weather", "cities": [], "days": None,
                    "budget": None, "weather_city": "鸡西",
                    "is_continuation": False, "confidence": 0.9})
    out = asyncio.run(build_understand_chain(model=m).ainvoke(
        {"message": "鸡西最近天气", "history": []}))
    assert out.intent == "weather"
    assert out.weather_city == "鸡西"


def test_understand_continuation_inherits_city():
    """承接上文（"细化下"）+ 从历史继承城市。"""
    hist = [{"role": "user", "content": "规划三亚5日游"},
            {"role": "assistant", "content": "好的，已为您规划"}]
    m = _json_model({"intent": "plan", "cities": ["三亚"], "days": 5,
                    "budget": None, "weather_city": None,
                    "is_continuation": True, "confidence": 0.9})
    out = asyncio.run(build_understand_chain(model=m).ainvoke(
        {"message": "细化下", "history": hist}))
    assert out.is_continuation is True
    assert out.cities == ["三亚"]


def test_understand_fallback_on_exception():
    """LLM 异常 → 安全降级 qa + confidence=0（触发 chat() 走规则兜底）。"""
    class Boom(SeqChatModel):
        def _generate(self, messages, **kwargs):
            raise RuntimeError("boom")
        async def _agenerate(self, messages, **kwargs):
            raise RuntimeError("boom")

    out = asyncio.run(build_understand_chain(model=Boom()).ainvoke(
        {"message": "随便说点", "history": []}))
    assert out.intent == "qa"
    assert out.confidence == 0.0


def test_understand_low_confidence_flagged():
    """低置信度透传，供 chat() 决定是否回退规则。"""
    m = _json_model({"intent": "qa", "cities": [], "days": None,
                    "budget": None, "weather_city": None,
                    "is_continuation": False, "confidence": 0.2})
    out = asyncio.run(build_understand_chain(model=m).ainvoke(
        {"message": "你好", "history": []}))
    assert out.confidence == 0.2
