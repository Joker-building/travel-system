"""天气经纬度解析回归：静态白名单优先 + Open-Meteo 地理编码兜底。

零真实网络（地理编码路径用 unittest.mock 拦截 httpx.AsyncClient）。
"""
import asyncio
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# 地理编码动态解析（白名单未命中时）
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


def test_geocode_dynamic_hit():
    """白名单外城市（腾冲）经地理编码解析出经纬度。"""
    WeatherService._GEOCODE_CACHE.pop("腾冲", None)
    payload = {"results": [{"latitude": 25.0, "longitude": 98.5}]}
    with patch("services.weather_service.httpx.AsyncClient",
               return_value=_FakeClient(payload)):
        coords = asyncio.run(WeatherService()._resolve_coords("腾冲"))
    assert coords == (25.0, 98.5)
    # 命中后写入缓存，二次解析不再触发网络
    assert WeatherService._GEOCODE_CACHE.get("腾冲") == (25.0, 98.5)
    WeatherService._GEOCODE_CACHE.pop("腾冲", None)


def test_geocode_empty_results_returns_none():
    """地理编码无结果时返回 None（上层降级模拟，不抛异常）。"""
    WeatherService._GEOCODE_CACHE.pop(" nonexistent_city_xyz", None)
    payload = {"results": []}
    with patch("services.weather_service.httpx.AsyncClient",
               return_value=_FakeClient(payload)):
        coords = asyncio.run(WeatherService()._resolve_coords("nonexistent_city_xyz"))
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
    with patch("services.weather_service.httpx.AsyncClient",
               return_value=_BoomClient()):
        coords = asyncio.run(WeatherService()._resolve_coords("boomcity"))
    assert coords is None
    WeatherService._GEOCODE_CACHE.pop("boomcity", None)
