"""Phase 4 单测：intent_chain / router_chain / build_chat_chain 顶层编排。

覆盖：
- intent_chain（决策① LLM 分类）：plan / weather / qa 分类 + 异常降级为 qa
- router_chain：RunnableBranch 按 is_plan / is_weather 路由到对应子链（链内嵌链）
- build_chat_chain 端到端（mock LLM + mock history_loader + 注入天气）：
    * plan 分支：确定性 is_plan_det 守门 → tool_calls 解析 → M8 输出 itinerary
    * qa 分支：→ M8 输出 question_answer
    * weather_qa 分支：is_weather_det 注入天气 → qa 分支收到天气 prompt
    * LLM 意图驱动：intent.is_plan / is_weather 触发对应分支（is_plan_det 为假时）
    * M1 城市约束：多城市文本序 cities[0] 作为 primary_city 注入 system prompt
    * M8 统一输出：{response_type, data, error_code} 结构

全部零真实 LLM / 零网络调用。
"""
import asyncio
import json

from langchain_core.runnables import RunnableLambda

from services.langchain_layer.chains.intent_chain import build_intent_chain
from services.langchain_layer.chains.router_chain import build_router_chain
from services.langchain_layer.chains.plan_chain import build_plan_chain
from services.langchain_layer.chains.qa_chain import build_qa_chain
from services.langchain_layer.orchestrator import build_chat_chain
from services.ai_service import AIService, ITINERARY_TOOL

from tests.chain_fakes import SeqChatModel, FakeWeatherService


# ---------- 辅助假模型 ----------

class RecordingSeqModel(SeqChatModel):
    """在 SeqChatModel 基础上记录最后一次收到的 Langchain messages（用于断言 prompt 注入）。

    注意：不能覆盖 __init__（会破坏 pydantic 初始化），改用私有属性 _captured 记录。
    """

    def _generate(self, messages, **kwargs):
        self._captured = messages
        return super()._generate(messages, **kwargs)


class BoomModel(SeqChatModel):
    """_generate 直接抛异常，用于验证 intent_chain 异常降级。"""

    def _generate(self, messages, **kwargs):
        raise RuntimeError("llm unavailable")

    async def _agenerate(self, messages, **kwargs):
        raise RuntimeError("llm unavailable")


def _json_model(obj):
    """构造「返回 JSON 文本」的 SeqChatModel（intent / qa 用）。"""
    return SeqChatModel(responses=[{"content": json.dumps(obj, ensure_ascii=False), "tool_calls": []}])


def _all_contents(model):
    """把 RecordingSeqModel 捕获的 Langchain messages 的 content 拼成字符串。"""
    msgs = getattr(model, "_captured", None) or []
    return " ".join(str(getattr(m, "content", "")) for m in msgs)


# 注入用的占位工具定义（plan_chain 仅需要结构，不实际调用模型工具）
_DUMMY_TOOL = [{
    "type": "function",
    "function": {
        "name": "create_itinerary",
        "description": "占位工具（单测）",
        "parameters": {"type": "object", "properties": {}},
    },
}]


# ============ intent_chain（决策①：LLM 分类替代纯规则）============

def test_intent_chain_classifies_plan():
    """LLM 返回 is_plan=True → 输出 is_plan True、is_weather 被强制 False。"""
    model = _json_model({"is_plan": True, "is_weather": False, "is_qa": False})
    chain = build_intent_chain(model=model)
    out = asyncio.run(chain.ainvoke({"message": "规划武汉3日游", "history": []}))
    assert out == {"is_plan": True, "is_weather": False, "is_qa": False}


def test_intent_chain_classifies_weather():
    """LLM 返回 is_weather=True（且非 plan）→ is_weather True，is_qa 仍 True（互斥兜底）。"""
    model = _json_model({"is_plan": False, "is_weather": True, "is_qa": True})
    chain = build_intent_chain(model=model)
    out = asyncio.run(chain.ainvoke({"message": "北京明天天气", "history": []}))
    assert out["is_plan"] is False
    assert out["is_weather"] is True
    assert out["is_qa"] is True


def test_intent_chain_classifies_qa_only():
    """LLM 返回三者皆否 / 仅 is_qa → 兜底 is_qa True。"""
    model = _json_model({"is_plan": False, "is_weather": False, "is_qa": True})
    chain = build_intent_chain(model=model)
    out = asyncio.run(chain.ainvoke({"message": "故宫几点开门", "history": []}))
    assert out == {"is_plan": False, "is_weather": False, "is_qa": True}


def test_intent_chain_degrades_to_qa_on_exception():
    """LLM 调用异常 → 安全降级为 qa（最保守，绝误触发行程/天气）。"""
    chain = build_intent_chain(model=BoomModel())
    out = asyncio.run(chain.ainvoke({"message": "随便说点", "history": []}))
    assert out == {"is_plan": False, "is_weather": False, "is_qa": True}


# ============ router_chain（RunnableBranch：链内嵌链路由）============

def _stub_plan():
    return RunnableLambda(lambda x: {"tool_calls": [{"name": "create_itinerary",
                                                     "args": {"trip": {}}, "id": "1", "type": "function"}],
                                     "content": ""})


def _stub_qa():
    return RunnableLambda(lambda x: {"response_type": "question_answer", "answer": "stub"})


def test_router_routes_to_plan_when_is_plan():
    """is_plan=True → 走 plan_chain（输出含 tool_calls）。"""
    router = build_router_chain(plan_chain=_stub_plan(), qa_chain=_stub_qa(), tools=_DUMMY_TOOL)
    out = asyncio.run(router.ainvoke({"messages": [], "is_plan": True, "is_weather": False}))
    assert "tool_calls" in out


def test_router_routes_to_qa_when_is_weather():
    """is_weather=True 且 is_plan=False → 走 qa_chain。"""
    router = build_router_chain(plan_chain=_stub_plan(), qa_chain=_stub_qa(), tools=_DUMMY_TOOL)
    out = asyncio.run(router.ainvoke({"messages": [], "is_plan": False, "is_weather": True}))
    assert out.get("answer") == "stub"


def test_router_default_branch_is_qa():
    """is_plan / is_weather 皆 False → 默认分支 qa_chain。"""
    router = build_router_chain(plan_chain=_stub_plan(), qa_chain=_stub_qa(), tools=_DUMMY_TOOL)
    out = asyncio.run(router.ainvoke({"messages": [], "is_plan": False, "is_weather": False}))
    assert out.get("answer") == "stub"


# ============ build_chat_chain 顶层编排（多链 + 嵌套 + 并发）============

def _build_plan_qa_router(plan_model, qa_model):
    """构造「注入模型」的 router：plan/qa 子链分别用各自假模型，便于断言与离线。"""
    plan_chain = build_plan_chain(model=plan_model, tools=_DUMMY_TOOL)
    qa_chain = build_qa_chain(model=qa_model)
    return build_router_chain(plan_chain=plan_chain, qa_chain=qa_chain, tools=_DUMMY_TOOL)


def test_chat_chain_plan_branch_m8_and_m1_city_constraint():
    """plan 分支：is_plan_det 确定性守门 → 解析 tool_calls → M8 itinerary；
    且 system prompt 按文本序把 cities[0]='武汉' 作为目的城市约束（M1 修复）。"""
    plan_model = RecordingSeqModel(responses=[{
        "content": "",
        "tool_calls": [{
            "name": "create_itinerary",
            "args": {"trip": {"travel_days": 3}, "narrative": "行程...", "chat_title": "武汉3日游规划"},
            "id": "1", "type": "function",
        }],
    }])
    qa_model = _json_model({"response_type": "question_answer", "data": {"answer": "x"}})
    router = _build_plan_qa_router(plan_model, qa_model)

    chain = build_chat_chain(
        intent_chain=RunnableLambda(lambda x: {"is_plan": False, "is_weather": False, "is_qa": True}),
        router_chain=router,
        history_loader=lambda i: {},
        weather_service=FakeWeatherService("[W]"),
        plan_tools=_DUMMY_TOOL,
    )
    out = asyncio.run(chain.ainvoke({
        "message": "武汉3日游", "history": [], "weather": {"city": "武汉", "days": 3},
        "prefs": {}, "cities": ["武汉"], "days": 3, "budget": None,
        "is_plan_det": True, "is_weather_det": False,
    }))

    # M8 统一输出结构
    assert out["response_type"] == "itinerary"
    assert out["error_code"] is None
    assert isinstance(out["data"], dict)
    assert out["data"]["trip"]["travel_days"] == 3

    # M1：system prompt 明确把 cities[0]='武汉' 作为目的城市，且约束 travel_days=3
    sys_text = _all_contents(plan_model)
    assert "武汉" in sys_text and "dest_city" in sys_text
    assert "travel_days 必须严格等于 3" in sys_text


def test_chat_chain_qa_branch_m8():
    """qa 分支：is_plan_det/is_weather_det 皆 False → M8 question_answer。"""
    plan_model = RecordingSeqModel(responses=[{"tool_calls": [{"name": "create_itinerary",
                                                              "args": {}, "id": "1", "type": "function"}]}])
    qa_model = _json_model({"response_type": "question_answer",
                            "data": {"chat_title": "问答", "answer": "故宫8:30开门"}})
    router = _build_plan_qa_router(plan_model, qa_model)

    chain = build_chat_chain(
        intent_chain=RunnableLambda(lambda x: {"is_plan": False, "is_weather": False, "is_qa": True}),
        router_chain=router,
        history_loader=lambda i: {},
        weather_service=FakeWeatherService("[W]"),
        plan_tools=_DUMMY_TOOL,
    )
    out = asyncio.run(chain.ainvoke({
        "message": "故宫几点开门", "history": [], "weather": {"city": "", "days": 3},
        "prefs": {}, "cities": [], "days": None, "budget": None,
        "is_plan_det": False, "is_weather_det": False,
    }))
    assert out["response_type"] == "question_answer"
    assert out["error_code"] is None
    assert out["data"]["answer"] == "故宫8:30开门"


def test_chat_chain_weather_qa_branch_injects_weather():
    """weather_qa 分支：is_weather_det=True → 注入天气 prompt，qa 子链收到天气数据。"""
    plan_model = RecordingSeqModel(responses=[{"tool_calls": [{"name": "create_itinerary",
                                                              "args": {}, "id": "1", "type": "function"}]}])
    qa_model = RecordingSeqModel(responses=[{
        "content": json.dumps({"response_type": "question_answer",
                               "data": {"chat_title": "天气", "answer": "北京明天晴"}}, ensure_ascii=False),
        "tool_calls": [],
    }])
    router = _build_plan_qa_router(plan_model, qa_model)

    chain = build_chat_chain(
        intent_chain=RunnableLambda(lambda x: {"is_plan": False, "is_weather": False, "is_qa": True}),
        router_chain=router,
        history_loader=lambda i: {},
        weather_service=FakeWeatherService("[WX]"),
        plan_tools=_DUMMY_TOOL,
    )
    out = asyncio.run(chain.ainvoke({
        "message": "北京明天天气", "history": [], "weather": {"city": "北京", "days": 1},
        "prefs": {}, "cities": [], "days": None, "budget": None,
        "is_plan_det": False, "is_weather_det": True,
    }))
    assert out["response_type"] == "question_answer"
    assert out["data"]["answer"] == "北京明天晴"
    # 天气注入：qa 子链收到的 system prompt 含注入的天气文本
    assert "[WX]" in _all_contents(qa_model)


def test_chat_chain_llm_intent_drives_plan_when_det_false():
    """LLM 意图驱动（决策①）：is_plan_det=False 但 intent.is_plan=True → 仍走 plan 分支。"""
    plan_model = RecordingSeqModel(responses=[{
        "content": "",
        "tool_calls": [{"name": "create_itinerary",
                        "args": {"trip": {"travel_days": 2}, "narrative": "x", "chat_title": "宜昌2日游"},
                        "id": "1", "type": "function"}],
    }])
    qa_model = _json_model({"response_type": "question_answer", "data": {"answer": "x"}})
    router = _build_plan_qa_router(plan_model, qa_model)

    chain = build_chat_chain(
        intent_chain=RunnableLambda(lambda x: {"is_plan": True, "is_weather": False, "is_qa": False}),
        router_chain=router,
        history_loader=lambda i: {},
        weather_service=FakeWeatherService("[W]"),
        plan_tools=_DUMMY_TOOL,
    )
    out = asyncio.run(chain.ainvoke({
        "message": "帮我安排下宜昌的行程", "history": [], "weather": {"city": "宜昌", "days": 2},
        "prefs": {}, "cities": ["宜昌"], "days": 2, "budget": None,
        "is_plan_det": False, "is_weather_det": False,  # 确定性未命中，靠 LLM 分类
    }))
    assert out["response_type"] == "itinerary"
    assert out["data"]["trip"]["travel_days"] == 2


def test_chat_chain_llm_intent_drives_weather_when_det_false():
    """LLM 意图驱动：is_weather_det=False 但 intent.is_weather=True → 走天气问答分支。"""
    plan_model = RecordingSeqModel(responses=[{"tool_calls": [{"name": "create_itinerary",
                                                              "args": {}, "id": "1", "type": "function"}]}])
    qa_model = RecordingSeqModel(responses=[{
        "content": json.dumps({"response_type": "question_answer",
                               "data": {"answer": "上海后天多云"}}, ensure_ascii=False),
        "tool_calls": [],
    }])
    router = _build_plan_qa_router(plan_model, qa_model)

    chain = build_chat_chain(
        intent_chain=RunnableLambda(lambda x: {"is_plan": False, "is_weather": True, "is_qa": True}),
        router_chain=router,
        history_loader=lambda i: {},
        weather_service=FakeWeatherService("[WS]"),
        plan_tools=_DUMMY_TOOL,
    )
    out = asyncio.run(chain.ainvoke({
        "message": "上海天气怎么样", "history": [], "weather": {"city": "上海", "days": 1},
        "prefs": {}, "cities": [], "days": None, "budget": None,
        "is_plan_det": False, "is_weather_det": False,
    }))
    assert out["response_type"] == "question_answer"
    assert out["data"]["answer"] == "上海后天多云"


# ============ M1 直接单测：_assemble_messages 多城市文本序约束 ============

def test_assemble_messages_multi_city_uses_text_order_primary():
    """M1 修复核心：多城市时 primary_city = 文本序 cities[0]，dest_city 用主要城市，
    且所有提及城市都进入约束（不再用 _extract_city 的固定列表序）。"""
    messages = AIService._assemble_messages(
        message="武汉到宜昌及恩施3日游", history_messages=[], weather_prompt="",
        cities=["武汉", "宜昌", "恩施"], days=3, budget=None, is_plan=True,
    )
    system = messages[0]["content"]
    # 主要城市（文本序首发）= 武汉
    assert "主要城市「武汉」" in system
    assert "dest_city 字段使用主要城市「武汉」" in system
    # 所有提及城市都被纳入，且无城市被遗漏
    for c in ("武汉", "宜昌", "恩施"):
        assert c in system
    # 天数约束
    assert "travel_days 必须严格等于 3" in system


def test_assemble_messages_single_city_constraint():
    """单城市：dest_city 必须严格等于该城市。"""
    messages = AIService._assemble_messages(
        message="武汉3日游", history_messages=[], weather_prompt="",
        cities=["武汉"], days=None, budget=None, is_plan=True,
    )
    system = messages[0]["content"]
    assert "目的地城市是：武汉" in system
    assert "必须严格等于「武汉」" in system
