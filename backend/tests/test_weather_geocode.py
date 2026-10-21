"""天气经纬度解析回归：静态白名单优先 + 和风地理编码（配 key 时）+ Open-Meteo 兜底。

零真实网络（地理编码路径用 unittest.mock 拦截 httpx.AsyncClient / ProxyService）。
"""
import asyncio
from unittest.mock import patch

from config import settings
from services.weather_service import WeatherService


# ---------------------------------------------------------------------------
# 静态白名单（离线可靠快路径）
# ---------------------------------------------------------------------------
def test_resolve_coords_static_jixi():
    """鸡西已补入静态白名单，离线即可解析，无需走网络。"""
    coords = asyncio.run(WeatherService()._resolve_coords("鸡西"))
    assert coords == (45.30, 130.97)


def test_resolve_coords_static_shenzhen():
    """既有白名单城市仍正常。"""
    coords = asyncio.run(WeatherService()._resolve_coords("深圳"))
    assert coords == (22.54, 114.06)


def test_resolve_coords_static_xianning():
    """咸宁已补入静态白名单（湖北温泉目的地），离线即可解析。"""
    coords = asyncio.run(WeatherService()._resolve_coords("咸宁"))
    assert coords == (29.8572, 114.2772)


# ---------------------------------------------------------------------------
# 和风地理编码（B 路线：配和风 key 后，白名单外城市也能解析，国内源）
# ---------------------------------------------------------------------------
def test_geocode_via_qweather_hit():
    """白名单外城市（神农架）在已配置和风时经和风地理编码解析，不再依赖境外 Open-Meteo。"""
    old_host, old_key = settings.QWEATHER_HOST, settings.QWEATHER_KEY
    settings.QWEATHER_HOST, settings.QWEATHER_KEY = "devapi.qweather.com", "test-key"
    WeatherService._GEOCODE_CACHE.pop("神农架", None)
    try:
        async def _fake_geo(self, city):
            return {"code": "200", "location": [{"name": city, "lat": "31.45", "lon": "110.40"}]}

        class _BoomClient:  # 若回退到 Open-Meteo 则报错，证明和风路径生效
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url, params=None):
                raise AssertionError("Open-Meteo 不应被调用（和风应已命中）")

        with patch("services.proxy_service.ProxyService.qweather_geo", _fake_geo):
            with patch("services.weather_service.httpx.AsyncClient", return_value=_BoomClient()):
                coords = asyncio.run(WeatherService()._resolve_coords("神农架"))
        assert coords == (31.45, 110.40)
        assert WeatherService._GEOCODE_CACHE.get("神农架") == (31.45, 110.40)
    finally:
        settings.QWEATHER_HOST, settings.QWEATHER_KEY = old_host, old_key
        WeatherService._GEOCODE_CACHE.pop("神农架", None)


def test_geocode_qweather_fail_falls_through_open_meteo():
    """和风地理编码失败（如 key 失效）时，回退 Open-Meteo 地理编码。"""
    old_host, old_key = settings.QWEATHER_HOST, settings.QWEATHER_KEY
    settings.QWEATHER_HOST, settings.QWEATHER_KEY = "devapi.qweather.com", "test-key"
    WeatherService._GEOCODE_CACHE.pop("神农架", None)
    try:
        async def _boom_geo(self, city):
            return {"code": "401", "message": "invalid key"}

        payload = {"results": [{"latitude": 31.45, "longitude": 110.40}]}
        with patch("services.proxy_service.ProxyService.qweather_geo", _boom_geo):
            with patch("services.weather_service.httpx.AsyncClient", return_value=_FakeClient(payload)):
                coords = asyncio.run(WeatherService()._resolve_coords("神农架"))
        assert coords == (31.45, 110.40)
    finally:
        settings.QWEATHER_HOST, settings.QWEATHER_KEY = old_host, old_key
        WeatherService._GEOCODE_CACHE.pop("神农架", None)


# ---------------------------------------------------------------------------
# Open-Meteo 地理编码兜底（和风未配置时）
# ---------------------------------------------------------------------------
class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None):
        return _FakeResp(self._payload)


def _with_qweather_disabled(test_fn):
    """装饰器：临时中和 QWEATHER 配置，确保只走 Open-Meteo 兜底分支。"""
    old_host, old_key = settings.QWEATHER_HOST, settings.QWEATHER_KEY
    settings.QWEATHER_HOST = settings.QWEATHER_KEY = ""
    try:
        return test_fn()
    finally:
        settings.QWEATHER_HOST, settings.QWEATHER_KEY = old_host, old_key


def test_geocode_dynamic_hit():
    """白名单外城市（腾冲）经 Open-Meteo 地理编码解析出经纬度（和风未配置时）。"""
    WeatherService._GEOCODE_CACHE.pop("腾冲", None)
    payload = {"results": [{"latitude": 25.0, "longitude": 98.5}]}

    def _run():
        with patch("services.weather_service.httpx.AsyncClient", return_value=_FakeClient(payload)):
            return asyncio.run(WeatherService()._resolve_coords("腾冲"))

    coords = _with_qweather_disabled(_run)
    assert coords == (25.0, 98.5)
    assert WeatherService._GEOCODE_CACHE.get("腾冲") == (25.0, 98.5)
    WeatherService._GEOCODE_CACHE.pop("腾冲", None)


def test_geocode_empty_results_returns_none():
    """地理编码无结果时返回 None（上层降级模拟，不抛异常）。"""
    WeatherService._GEOCODE_CACHE.pop("nonexistent_city_xyz", None)
    payload = {"results": []}

    def _run():
        with patch("services.weather_service.httpx.AsyncClient", return_value=_FakeClient(payload)):
            return asyncio.run(WeatherService()._resolve_coords("nonexistent_city_xyz"))

    coords = _with_qweather_disabled(_run)
    assert coords is None
    WeatherService._GEOCODE_CACHE.pop("nonexistent_city_xyz", None)


def test_geocode_network_failure_returns_none():
    """境外网络 TCP 重置 / 超时等异常时返回 None，不引入回归。"""

    class _BoomClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, params=None):
            raise RuntimeError("TCP reset")

    WeatherService._GEOCODE_CACHE.pop("boomcity", None)

    def _run():
        with patch("services.weather_service.httpx.AsyncClient", return_value=_BoomClient()):
            return asyncio.run(WeatherService()._resolve_coords("boomcity"))

    coords = _with_qweather_disabled(_run)
    assert coords is None
    WeatherService._GEOCODE_CACHE.pop("boomcity", None)
