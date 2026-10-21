"""测试 ProxyService.qweather_geo 的多候选地址回退逻辑（零真实网络）。

覆盖三种订阅形态：
1. 标准订阅：geo 与天气同主机 /geo/v2/city/lookup 命中；
2. 免费开发者版：标准路径 404 后回退 geoapi.qweather.com/v2 命中；
3. 全部失败：返回 code=404 且带候选失败信息。
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from services.proxy_service import ProxyService


class _Resp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    """按序消费预置响应，模拟多次候选请求。"""

    def __init__(self, responses):
        self._responses = responses
        self._i = 0
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        r = self._responses[self._i]
        self.calls.append(url)
        self._i += 1
        return r


@pytest.fixture
def fake_settings(monkeypatch):
    """临时把 QWEATHER_HOST/KEY 设成非空，避免提前 return 401。"""
    import config

    monkeypatch.setattr(config.settings, "QWEATHER_HOST", "myhost.qweatherapi.com")
    monkeypatch.setattr(config.settings, "QWEATHER_KEY", "test-key")
    # 默认 geo 主机保持内置默认，不显式设置
    monkeypatch.setattr(config.settings, "QWEATHER_GEO_HOST", "geoapi.qweather.com")
    return config.settings


def test_standard_subscription_geo_path_hit(monkeypatch, fake_settings):
    """标准订阅：同主机 /geo/v2/city/lookup 应被优先命中，不请求 geoapi。"""
    ok = _Resp(200, {"code": "200", "location": [{"name": "萍乡", "lat": "27.62", "lon": "113.85"}]})
    client = _FakeClient([ok])
    with patch("services.proxy_service.httpx.AsyncClient", return_value=client):
        data = asyncio.run(ProxyService().qweather_geo("萍乡"))
    assert data.get("code") == "200"
    assert data["location"][0]["name"] == "萍乡"
    # 第一个候选即命中，不应出现 geoapi.qweather.com
    assert all("geoapi.qweather.com" not in u for u in client.calls)


def test_dev_tier_fallback_after_404(monkeypatch, fake_settings):
    """开发者版：标准路径 404，应回退到 geoapi.qweather.com/v2 并命中。"""
    not_found = _Resp(404, {})
    ok = _Resp(200, {"code": "200", "location": [{"name": "萍乡", "lat": "27.62", "lon": "113.85"}]})
    client = _FakeClient([not_found, ok])
    with patch("services.proxy_service.httpx.AsyncClient", return_value=client):
        data = asyncio.run(ProxyService().qweather_geo("萍乡"))
    assert data.get("code") == "200"
    assert client.calls[0].startswith("https://myhost.qweatherapi.com/geo/v2/city/lookup")
    assert client.calls[1] == "https://geoapi.qweather.com/v2/city/lookup"


def test_all_candidates_fail_returns_404(monkeypatch, fake_settings):
    """全部候选失败：返回 code=404 且携带候选失败信息。"""
    fail1 = _Resp(404, {})
    fail2 = _Resp(403, {"code": "403", "message": "forbidden"})
    client = _FakeClient([fail1, fail2])
    with patch("services.proxy_service.httpx.AsyncClient", return_value=client):
        data = asyncio.run(ProxyService().qweather_geo("未知城市"))
    assert data.get("code") == "404"
    assert "全部候选失败" in data.get("message", "")


def test_missing_config_returns_401(monkeypatch):
    """未配置和风密钥时直接返回 401，不发请求。"""
    import config

    monkeypatch.setattr(config.settings, "QWEATHER_HOST", "")
    monkeypatch.setattr(config.settings, "QWEATHER_KEY", "")
    data = asyncio.run(ProxyService().qweather_geo("萍乡"))
    assert data.get("code") == "401"
