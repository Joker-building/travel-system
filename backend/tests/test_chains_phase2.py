"""Phase 2 链单测：零真实 LLM / 零网络，全部用 chain_fakes 注入。

覆盖：
- weather_chain: 成功 / 失败降级 / 无 city
- qa_chain: 正常 QA / 空回复经 with_fallbacks 重试成功
- plan_chain: 正常 tool_calls / 空调用经 with_fallbacks 重试成功
- scenic_search_chain: 多候选 / 单对象自动包装 / 空结果
- scenic_detail_chain: 只读详情
"""
import asyncio

from services.langchain_layer.chains.weather_chain import build_weather_chain
from services.langchain_layer.chains.qa_chain import build_qa_chain
from services.langchain_layer.chains.plan_chain import build_plan_chain
from services.langchain_layer.chains.scenic_search_chain import build_scenic_search_chain
from services.langchain_layer.chains.scenic_detail_chain import build_scenic_detail_chain
from tests.chain_fakes import SeqChatModel, FakeWeatherService


def run(coro):
    return asyncio.run(coro)


SAMPLE_MESSAGES = [
    {"role": "system", "content": "你是旅游助手"},
    {"role": "user", "content": "武汉有什么好玩的"},
]


# ---------------- weather_chain ----------------
def test_weather_success():
    chain = build_weather_chain(weather_service=FakeWeatherService(prompt="[W]"))
    out = run(chain.ainvoke({"city": "武汉", "days": 3}))
    assert out["success"] is True
    assert "武汉" in out["prompt"]


def test_weather_failure_degrade():
    # 假服务抛异常 → 降级 success=False，且不向上抛
    chain = build_weather_chain(weather_service=FakeWeatherService(fail=True))
    out = run(chain.ainvoke({"city": "武汉", "days": 3}))
    assert out == {"success": False, "prompt": ""}


def test_weather_no_city():
    chain = build_weather_chain(weather_service=FakeWeatherService())
    out = run(chain.ainvoke({"city": None, "days": 3}))
    assert out == {"success": False, "prompt": ""}


# ---------------- qa_chain ----------------
QA_OK = '{"response_type":"question_answer","data":{"chat_title":"武汉游玩","answer":"东湖很不错"}}'


def test_qa_happy():
    model = SeqChatModel(responses=[{"content": QA_OK}])
    chain = build_qa_chain(model=model)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert out["answer"] == "东湖很不错"
    assert out["chat_title"] == "武汉游玩"  # data 子字段已上提


def test_qa_empty_then_retry():
    # 主链返回空 content（解析失败）→ 经 with_fallbacks 追加补注重试 → 拿到真实答案
    model = SeqChatModel(responses=[
        {"content": ""},
        {"content": '{"response_type":"question_answer","data":{"chat_title":"重试","answer":"重试成功"}}'},
    ])
    chain = build_qa_chain(model=model)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert out["answer"] == "重试成功"  # 说明兜底重试链真的跑了第二次调用


# ---------------- plan_chain ----------------
PLAN_TOOL = [{"type": "function", "function": {"name": "create_itinerary", "parameters": {}}}]
TOOL_OK = [{"name": "create_itinerary", "args": {"trip": {"dest_city": "武汉"}}, "id": "1", "type": "function"}]


def test_plan_happy():
    model = SeqChatModel(responses=[{"tool_calls": TOOL_OK}])
    chain = build_plan_chain(model=model, tools=PLAN_TOOL)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["name"] == "create_itinerary"
    assert out[0]["args"]["trip"]["dest_city"] == "武汉"


def test_plan_empty_then_retry():
    model = SeqChatModel(responses=[
        {"content": ""},  # 主链无 tool_calls
        {"tool_calls": TOOL_OK},  # 重试补注后触发
    ])
    chain = build_plan_chain(model=model, tools=PLAN_TOOL)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert out[0]["name"] == "create_itinerary"  # 说明兜底重试链真的拿到 tool_calls


# ---------------- scenic_search_chain ----------------
SEARCH_OK = '{"results":[{"name":"东湖","city":"武汉","category":"自然风光"}]}'


def test_scenic_search_list():
    model = SeqChatModel(responses=[{"content": SEARCH_OK}])
    chain = build_scenic_search_chain(model=model)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert out["results"][0]["name"] == "东湖"


def test_scenic_search_single_object_wrapped():
    # 模型偶发返回单个对象（含 name）→ 自动包装为列表
    model = SeqChatModel(responses=[{"content": '{"name":"黄鹤楼","city":"武汉"}'}])
    chain = build_scenic_search_chain(model=model)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert isinstance(out["results"], list) and out["results"][0]["name"] == "黄鹤楼"


def test_scenic_search_empty():
    model = SeqChatModel(responses=[{"content": "{}"}])
    chain = build_scenic_search_chain(model=model)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert out["results"] == []


# ---------------- scenic_detail_chain（只读） ----------------
DETAIL_OK = '{"introduction":"明代楼阁","price":0,"special_notice":"登楼注意安全","budget_suggestion":"预留50元"}'


def test_scenic_detail_readonly():
    model = SeqChatModel(responses=[{"content": DETAIL_OK}])
    chain = build_scenic_detail_chain(model=model)
    out = run(chain.ainvoke({"messages": SAMPLE_MESSAGES}))
    assert out["introduction"] == "明代楼阁"
    assert out["price"] == 0
    assert out["budget_suggestion"] == "预留50元"
