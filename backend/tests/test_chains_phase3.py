"""Phase 3 context_chain 单测（mock LLM / mock 服务，零真实调用）。

覆盖：
- 输出结构（history / weather / prefs 三分支结果正确）
- weather 分支成功路径（注入 FakeWeatherService，验证 chain 内嵌 chain）
- loader 异常降级（history loader 抛异常不阻断主链）
- 并发验证（async）：三个分支被 RunnableParallel 异步并发执行，总耗时 < 串行
"""
import asyncio
import time

import pytest

from services.langchain_layer.chains.context_chain import build_context_chain


class FakeWeatherService:
    """模仿 WeatherService 的最小接口（async get + sync format）。"""

    async def get_weather_forecast(self, city, days=3):
        return {"success": True, "city": city, "days": days, "forecast": []}

    def format_weather_for_prompt(self, data):
        return f"[weather:{data.get('city')}]"


def test_context_chain_structure_and_weather_degrade():
    """默认 history/prefs loader 返回 {}；空 city 时 weather 降级 success=False。"""

    def hist_loader(inputs):
        return {"rows": [{"role": "user", "content": "你好"}]}

    def prefs_loader(inputs):
        return {"theme": "mountain"}

    chain = build_context_chain(history_loader=hist_loader, prefs_loader=prefs_loader)
    result = asyncio.run(chain.ainvoke({
        "history": {"session_id": 1},
        "weather": {"city": "", "days": 3},  # 空 city → 天气链降级
        "prefs": {"user_id": 2},
    }))
    assert result["history"] == {"rows": [{"role": "user", "content": "你好"}]}
    assert result["prefs"] == {"theme": "mountain"}
    assert result["weather"]["success"] is False
    assert result["weather"]["prompt"] == ""


def test_context_chain_weather_success_inner_chain():
    """weather 分支成功路径：注入 FakeWeatherService，验证 chain 内嵌 chain 生效。"""
    fake = FakeWeatherService()
    chain = build_context_chain(weather_service=fake)
    result = asyncio.run(chain.ainvoke({
        "weather": {"city": "北京", "days": 2},
    }))
    assert result["history"] == {}        # 默认 loader
    assert result["prefs"] == {}          # 默认 loader
    assert result["weather"]["success"] is True
    assert "北京" in result["weather"]["prompt"]


def test_context_chain_loader_failure_degrades():
    """history loader 抛异常应降级为 {}，且主链不抛异常继续。"""

    def boom(inputs):
        raise RuntimeError("db down")

    chain = build_context_chain(history_loader=boom)
    result = asyncio.run(chain.ainvoke({
        "history": {"x": 1},
        "weather": {"city": ""},
    }))
    assert result["history"] == {}          # 降级
    assert result["weather"]["success"] is False
    # 不抛异常即通过（主链继续）


@pytest.mark.asyncio
async def test_context_chain_concurrent_execution():
    """三个分支被 RunnableParallel 异步并发：总耗时 < 串行耗时（验证并发）。"""
    calls = []
    order = []

    async def slow_hist(inputs):
        order.append(("history_start", time.monotonic()))
        await asyncio.sleep(0.06)
        calls.append("history")
        order.append(("history_end", time.monotonic()))
        return {"h": 1}

    async def slow_prefs(inputs):
        order.append(("prefs_start", time.monotonic()))
        await asyncio.sleep(0.06)
        calls.append("prefs")
        order.append(("prefs_end", time.monotonic()))
        return {"p": 1}

    chain = build_context_chain(history_loader=slow_hist, prefs_loader=slow_prefs)
    start = time.monotonic()
    result = await chain.ainvoke({
        "history": {"session_id": 1},
        "weather": {"city": ""},   # 快速降级，不拖慢
        "prefs": {"user_id": 2},
    })
    elapsed = time.monotonic() - start

    # 串行预期 ≈ 0.06 + 0.06 = 0.12s；并发预期 ≈ 0.06s（含事件循环开销 < 0.10）
    assert elapsed < 0.10, f"期望并发(总耗时<0.10s)，实际 {elapsed:.3f}s（疑似串行）"
    assert set(calls) == {"history", "prefs"}
    assert result["history"] == {"h": 1}
    assert result["prefs"] == {"p": 1}

    # 进一步证明重叠：history 与 prefs 的起始时间差应远小于单个 sleep 时长
    hist_start = next(t for k, t in order if k == "history_start")
    prefs_start = next(t for k, t in order if k == "prefs_start")
    overlap_gap = abs(hist_start - prefs_start)
    assert overlap_gap < 0.03, f"两分支起始间隔 {overlap_gap:.3f}s，未并发启动"
