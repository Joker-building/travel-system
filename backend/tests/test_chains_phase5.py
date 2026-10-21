"""Phase 5 测试：M3（print → logging）、M5（search_scenic 默认不落库）、M6（get_scenic_detail 只读）。

零真实 LLM / 零网络：所有外部调用经 monkeypatch 替换。
"""
import asyncio
import json
import logging

from services import ai_service as ai_module
from services.ai_service import AIService
from services import weather_service as weather_module
from services import voice_service as voice_module


# ---------------------------------------------------------------------------
# M3：logging 已落地（替代全量 print）
# ---------------------------------------------------------------------------
def test_logger_present_on_service_modules():
    """三个服务模块都应持有 logger，而非再用 print 调试。"""
    assert isinstance(getattr(ai_module, "logger", None), logging.Logger)
    assert isinstance(getattr(weather_module, "logger", None), logging.Logger)
    assert isinstance(getattr(voice_module, "logger", None), logging.Logger)


def test_search_scenic_failure_is_logged(caplog, monkeypatch):
    """search_scenic 异常分支应走 logger.error（M3），而非 print 到 stdout。"""
    async def boom(*a, **k):
        raise RuntimeError("mock api down")

    monkeypatch.setattr(AIService, "call_deepseek_api", boom)

    with caplog.at_level(logging.ERROR, logger="services.ai_service"):
        result = asyncio.run(AIService.search_scenic("x", "y"))

    assert result["success"] is False
    assert any("景点搜索失败" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# M5：search_scenic 默认不落库
# ---------------------------------------------------------------------------
def test_search_scenic_no_db_write(monkeypatch):
    """搜索结果默认不写 scenic_spot 表（修复 M5）：_find_or_create_scenic 不得被调用，卡片 id=None。"""
    fake_content = json.dumps({
        "results": [
            {"name": "黄鹤楼", "city": "武汉", "category": "古迹", "price": 60},
            {"name": "东湖", "city": "武汉", "category": "自然", "price": 0},
        ]
    })
    fake_raw = {"choices": [{"message": {"content": fake_content}}]}

    async def fake_call(*a, **k):
        return fake_raw

    monkeypatch.setattr(AIService, "call_deepseek_api", fake_call)

    writes = []
    orig = AIService._find_or_create_scenic

    def spy(db, spot):
        writes.append(spot)
        return orig(db, spot)

    monkeypatch.setattr(AIService, "_find_or_create_scenic", spy)

    result = asyncio.run(AIService.search_scenic("古迹", "武汉"))

    assert result["success"] is True
    assert result["total"] == 2
    assert writes == [], "search_scenic 不应写库（M5）"
    for r in result["results"]:
        assert r["id"] is None, "搜索卡片默认无 DB id（M5）"
        assert r["name"] in ("黄鹤楼", "东湖")


def test_search_scenic_handles_single_object(monkeypatch):
    """模型偶发返回单个对象（含 name）时应自动包装为列表。"""
    fake_content = json.dumps({"name": "黄鹤楼", "city": "武汉", "price": 60})
    fake_raw = {"choices": [{"message": {"content": fake_content}}]}
    async def fake_call(*a, **k):
        return fake_raw
    monkeypatch.setattr(AIService, "call_deepseek_api", fake_call)

    result = asyncio.run(AIService.search_scenic("黄鹤楼", "武汉"))
    assert result["success"] is True
    assert result["total"] == 1


# ---------------------------------------------------------------------------
# M6：get_scenic_detail 只读（删除 dead 落库分支）
# ---------------------------------------------------------------------------
def test_get_scenic_detail_read_only(monkeypatch):
    """详情接口只读（修复 M6）：不接收 db、不写库、返回体无 scenic_id。"""
    fake_content = json.dumps({
        "introduction": "江南三大名楼之一",
        "price": 60,
        "special_notice": "周一闭馆",
        "budget_suggestion": "门票 60 元",
    })
    fake_raw = {"choices": [{"message": {"content": fake_content}}]}
    async def fake_call(*a, **k):
        return fake_raw
    monkeypatch.setattr(AIService, "call_deepseek_api", fake_call)

    writes = []
    def spy(db, spot):
        writes.append(spot)
        return None
    monkeypatch.setattr(AIService, "_find_or_create_scenic", spy)

    # 调用签名不再接受 db（旧落库分支已删除）
    result = asyncio.run(AIService.get_scenic_detail("黄鹤楼", "武汉"))

    assert result["success"] is True
    assert "scenic_id" not in result, "M6：详情返回不应暴露 scenic_id"
    assert "detail" in result
    assert result["detail"]["introduction"] == "江南三大名楼之一"
    assert writes == [], "get_scenic_detail 不应写库（M6）"


def test_get_scenic_detail_validates_input():
    """缺少景点名/城市应直接返回失败，不触发 LLM。"""
    result = asyncio.run(AIService.get_scenic_detail("", "武汉"))
    assert result["success"] is False
    result2 = asyncio.run(AIService.get_scenic_detail("黄鹤楼", ""))
    assert result2["success"] is False
