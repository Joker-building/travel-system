"""天气服务：和风天气优先，Open-Meteo 兜底

数据来源策略：
0. 城市经纬度解析：静态白名单（离线可靠）优先；未命中且已配置和风时，经和风地理编码
   API（geoapi.qweather.com，国内源、复用 QWEATHER_KEY）动态解析任意中文城市；
   和风未配置时再回退 Open-Meteo 地理编码（境外，国内可能不可达）；解析失败走模拟。
1. 优先使用和风天气（国内服务，稳定；需配置 QWEATHER_HOST + QWEATHER_KEY，密钥仅服务端）；
2. 和风未配置或调用失败时，降级使用 Open-Meteo（境外免费接口，无需 Key，但国内网络可能不稳定）；
3. 两者均失败时，降级为季节性模拟数据。

任何降级都会在返回 dict 的 `warning` 字段与日志中给出明确提示，便于排障。
"""

import logging
import random
import time
import httpx
from typing import Optional
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger(__name__)


class WeatherService:
    """天气服务：和风优先，Open-Meteo 兜底"""

    # 城市经纬度映射（离线可靠快路径；覆盖常用旅行目的地 + 部分地级市）。
    # 未命中此表的城市会再由 Open-Meteo 地理编码 API 动态解析（见 _resolve_coords）。
    CITY_COORDS = {
        # —— 直辖市 / 省会 / 重点城市 ——
        "北京": (39.90, 116.40), "天津": (39.13, 117.20), "上海": (31.23, 121.47),
        "重庆": (29.56, 106.55), "石家庄": (38.04, 114.51), "太原": (37.87, 112.55),
        "呼和浩特": (40.84, 111.75), "沈阳": (41.80, 123.43), "长春": (43.82, 125.32),
        "哈尔滨": (45.80, 126.53), "南京": (32.04, 118.78), "杭州": (31.23, 120.15),
        "合肥": (31.86, 117.28), "福州": (26.07, 119.30), "南昌": (28.68, 115.86),
        "济南": (36.65, 117.12), "郑州": (34.75, 113.62), "武汉": (30.59, 114.31),
        "长沙": (28.23, 112.94), "广州": (23.13, 113.27), "深圳": (22.54, 114.06),
        "南宁": (22.82, 108.37), "海口": (20.04, 110.20), "成都": (30.67, 104.07),
        "贵阳": (26.65, 106.63), "昆明": (25.04, 102.71), "拉萨": (29.65, 91.11),
        "西安": (34.27, 108.95), "兰州": (36.06, 103.83), "西宁": (36.62, 101.78),
        "银川": (38.49, 106.23), "乌鲁木齐": (43.83, 87.62),
        # —— 华东热门 ——
        "苏州": (31.30, 120.62), "无锡": (31.49, 120.31), "常州": (31.81, 119.97),
        "徐州": (34.27, 117.18), "南通": (31.98, 120.89), "连云港": (34.60, 119.22),
        "扬州": (32.39, 119.41), "宁波": (29.87, 121.55), "温州": (27.99, 120.70),
        "嘉兴": (30.75, 120.76), "金华": (29.08, 119.65), "绍兴": (30.00, 120.58),
        "台州": (28.66, 121.43), "芜湖": (31.34, 118.38), "厦门": (24.48, 118.09),
        "泉州": (24.87, 118.59), "漳州": (24.51, 117.66), "九江": (29.71, 116.00),
        "景德镇": (29.27, 117.18), "青岛": (36.07, 120.38), "烟台": (37.54, 121.40),
        "威海": (37.51, 122.12), "泰安": (36.20, 117.13), "洛阳": (34.62, 112.45),
        "开封": (34.80, 114.31),
        # —— 华北 / 东北 ——
        "唐山": (39.63, 118.18), "秦皇岛": (39.94, 119.60), "保定": (38.87, 115.46),
        "张家口": (40.82, 114.88), "承德": (40.99, 117.96), "大同": (40.08, 113.30),
        "包头": (40.66, 109.84), "大连": (38.91, 121.61), "鞍山": (41.11, 123.00),
        "丹东": (40.12, 124.39), "锦州": (41.10, 121.13), "吉林": (43.84, 126.55),
        "延吉": (42.91, 129.51), "牡丹江": (44.55, 129.60), "佳木斯": (46.81, 130.37),
        "大庆": (46.59, 125.03), "齐齐哈尔": (47.35, 123.92),
        "鸡西": (45.30, 130.97), "漠河": (53.00, 122.53),
        # —— 华中 / 华南 ——
        "襄阳": (32.01, 112.13), "珠海": (22.27, 113.58), "汕头": (23.35, 116.68),
        "佛山": (23.02, 113.12), "东莞": (23.02, 113.75), "桂林": (25.27, 110.29),
        "阳朔": (24.74, 110.29), "北海": (21.48, 109.12), "三亚": (18.25, 109.51),
        "柳州": (24.33, 109.42),
        # —— 湖北（全域补充：温泉 / 神农架 / 武当山等目的地） ——
        "咸宁": (29.8572, 114.2772), "黄石": (30.2006, 115.0351), "十堰": (32.6293, 110.7873),
        "荆州": (30.3371, 112.2386), "荆门": (31.0353, 112.2041), "鄂州": (30.3964, 114.8906),
        "孝感": (30.9167, 113.9333), "黄冈": (30.4534, 114.8793), "随州": (31.6922, 113.3718),
        # —— 西南 / 西北 ——
        "大理": (25.69, 100.16), "丽江": (26.87, 100.22), "香格里拉": (27.83, 99.71),
        "遵义": (27.73, 106.93), "景洪": (22.00, 100.80), "乐山": (29.55, 103.77),
        "敦煌": (40.14, 94.66), "喀什": (39.47, 75.99), "嘉峪关": (39.77, 98.29),
        # —— 旅行景区点 ——
        "恩施": (30.27, 109.49), "宜昌": (30.71, 111.29), "张家界": (29.12, 110.48),
        "黄山": (30.08, 118.31), "庐山": (29.55, 115.99), "岳阳": (29.36, 113.13),
        "凤凰": (27.95, 109.60),
    }

    # Open-Meteo 免费地理编码（无需 Key；解析任意中文地名 -> 经纬度，覆盖白名单外城市）
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    # 类名级缓存：跨 WeatherService 实例共享，避免同一城市重复请求
    _GEOCODE_CACHE: dict = {}

    # WMO 天气代码映射（Open-Meteo 使用 WMO 代码）
    WMO_CODE_MAP = {
        0: ("晴", "晴"),
        1: ("晴", "多云"),
        2: ("多云", "多云"),
        3: ("阴", "阴"),
        45: ("雾", "雾"),
        48: ("雾", "雾"),
        51: ("小雨", "小雨"),
        53: ("小雨", "小雨"),
        55: ("中雨", "中雨"),
        56: ("小雨", "小雨"),
        57: ("中雨", "中雨"),
        61: ("小雨", "小雨"),
        63: ("中雨", "中雨"),
        65: ("大雨", "大雨"),
        66: ("小雨", "小雨"),
        67: ("中雨", "中雨"),
        71: ("小雪", "小雪"),
        73: ("小雪", "小雪"),
        75: ("中雪", "中雪"),
        77: ("小雪", "小雪"),
        80: ("小雨", "小雨"),
        81: ("中雨", "中雨"),
        82: ("大雨", "大雨"),
        85: ("小雪", "小雪"),
        86: ("中雪", "中雪"),
        95: ("雷阵雨", "雷阵雨"),
        96: ("雷阵雨", "雷阵雨"),
        99: ("雷阵雨", "雷阵雨"),
    }

    # Open-Meteo API 地址（完全免费，无需 Key；作为兜底源）
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    # 各季节典型天气（用于降级模拟）
    SEASONAL_WEATHER = {
        "spring": [("晴", "多云", 15, 25), ("多云", "小雨", 12, 22), ("晴", "晴", 18, 28)],
        "summer": [("晴", "多云", 26, 35), ("雷阵雨", "多云", 25, 33), ("晴", "晴", 28, 38)],
        "autumn": [("晴", "晴", 15, 25), ("多云", "晴", 12, 22), ("小雨", "多云", 10, 20)],
        "winter": [("多云", "阴", 0, 10), ("晴", "晴", -2, 8), ("小雪", "多云", -5, 3)],
    }

    @staticmethod
    def _s(v) -> str:
        """安全转字符串（None -> 空串，避免 'None' 污染输出）"""
        return "" if v is None else str(v).strip()

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        """返回自 start 起经过的毫秒数（用于各阶段耗时统计）"""
        return (time.perf_counter() - start) * 1000

    def __init__(self, api_key: str = "", api_url: str = "", jwt_token: str = ""):
        # 和风密钥统一从 config.settings 读取，此处保留兼容签名
        pass

    @classmethod
    async def _geocode_via_open_meteo(cls, city: str) -> Optional[tuple]:
        """通过 Open-Meteo 地理编码将中文城市名解析为 (lat, lon)。

        免费、无需 Key；失败（境外网络 TCP 重置 / 超时 / 无结果）一律返回 None，
        由上层降级为模拟数据，不引入回归。结果按城市名缓存，避免重复请求。
        """
        if city in cls._GEOCODE_CACHE:
            return cls._GEOCODE_CACHE[city]
        try:
            params = {"name": city, "language": "zh", "count": 1, "format": "json"}
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(cls.GEOCODE_URL, params=params)
                data = resp.json()
            results = data.get("results") or []
            if not results:
                cls._GEOCODE_CACHE[city] = None
                return None
            geo = results[0]
            coords = (float(geo["latitude"]), float(geo["longitude"]))
            cls._GEOCODE_CACHE[city] = coords
            logger.info("[天气] Open-Meteo 地理编码命中: %s -> %s", city, coords)
            return coords
        except Exception as e:  # noqa: BLE001
            logger.warning("[天气] Open-Meteo 地理编码失败（境外接口可能不可达）: %s: %s",
                           type(e).__name__, e)
            cls._GEOCODE_CACHE[city] = None
            return None

    async def _geocode_via_qweather(self, city: str):
        """经和风地理编码解析中文城市名 -> (lat, lon)。

        国内源、复用 QWEATHER_KEY，覆盖白名单外城市（如咸宁）。失败（未配置 / 网络 /
        无结果）返回 None 并交由上层回退 Open-Meteo，不写入缓存（避免阻断兜底链路）。
        仅成功结果按城市名缓存。
        """
        if city in self._GEOCODE_CACHE:
            return self._GEOCODE_CACHE[city]
        if not (settings.QWEATHER_HOST and settings.QWEATHER_KEY):
            return None
        try:
            from services.proxy_service import ProxyService
            data = await ProxyService().qweather_geo(city)
            if str(data.get("code")) != "200":
                logger.warning(
                    "[天气] 和风地理编码失败: %s: %s", city, data.get("message", data.get("code"))
                )
                return None
            locs = data.get("location") or []
            if not locs:
                return None
            geo = locs[0]
            coords = (float(geo["lat"]), float(geo["lon"]))
            self._GEOCODE_CACHE[city] = coords
            logger.info("[天气] 和风地理编码命中: %s -> %s", city, coords)
            return coords
        except Exception as e:  # noqa: BLE001
            logger.warning("[天气] 和风地理编码异常: %s: %s", type(e).__name__, e)
            return None

    async def _resolve_coords(self, city: str) -> Optional[tuple]:
        """解析城市经纬度：静态白名单优先（离线可靠），未命中经和风地理编码
        （已配置时，国内源），最后回退 Open-Meteo 地理编码（境外）。"""
        coords = self.CITY_COORDS.get(city)
        if coords:
            return coords
        if settings.QWEATHER_HOST and settings.QWEATHER_KEY:
            coords = await self._geocode_via_qweather(city)
            if coords:
                return coords
        return await self._geocode_via_open_meteo(city)

    def _get_season(self) -> str:
        """根据当前月份判断季节"""
        month = datetime.now().month
        if 3 <= month <= 5:
            return "spring"
        elif 6 <= month <= 8:
            return "summer"
        elif 9 <= month <= 11:
            return "autumn"
        else:
            return "winter"

    def _generate_mock_weather(self, city: str, days: int = 3) -> dict:
        """生成季节性模拟天气数据（最终兜底方案）"""
        season = self._get_season()
        weather_options = self.SEASONAL_WEATHER.get(season, self.SEASONAL_WEATHER["spring"])
        forecasts = []

        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            idx = random.randint(0, len(weather_options) - 1)
            text_day, text_night, temp_min, temp_max = weather_options[idx]
            temp_min += random.randint(-2, 2)
            temp_max += random.randint(-2, 2)

            forecasts.append({
                "fxDate": date,
                "textDay": text_day,
                "textNight": text_night,
                "tempMax": str(temp_max),
                "tempMin": str(temp_min),
                "windDirDay": random.choice(["东风", "南风", "西风", "北风", "东南风"]),
                "windScaleDay": str(random.randint(1, 4)),
                "humidity": str(random.randint(40, 80)),
            })

        return {
            "success": True,
            "city": city,
            "forecasts": forecasts,
            "update_time": datetime.now().isoformat(),
            "source": "mock",
        }

    def _wmo_to_text(self, code: int) -> tuple:
        """WMO 天气代码转中文描述"""
        return self.WMO_CODE_MAP.get(code, ("未知", "未知"))

    # ---------- 和风天气（优先源） ----------

    def _normalize_qweather_daily(self, daily: list, days: int) -> list:
        """将和风 7d 接口的 daily 数组归一化为统一 forecasts 结构。

        和风 v7/weather/7d 的字段名（fxDate/textDay/textNight/tempMax/tempMin/
        windDirDay/windScaleDay/humidity）与本服务输出格式天然一致，几乎零转换。
        """
        forecasts = []
        for d in daily[:days]:
            forecasts.append({
                "fxDate": self._s(d.get("fxDate")),
                "textDay": self._s(d.get("textDay")),
                "textNight": self._s(d.get("textNight")),
                "tempMax": self._s(d.get("tempMax")),
                "tempMin": self._s(d.get("tempMin")),
                "windDirDay": self._s(d.get("windDirDay")),
                "windScaleDay": self._s(d.get("windScaleDay")),
                "humidity": self._s(d.get("humidity")),
            })
        return forecasts

    async def _fetch_from_qweather(self, city: str, days: int, coords: tuple):
        """尝试从和风天气获取预报。

        返回 (result_dict, error_msg)：
          - 成功：result_dict 为带 source='qweather' 的归一化结果，error_msg=None；
          - 失败：result_dict=None，error_msg 为可读原因。
        复用 proxy_service.ProxyService.qweather 以保持密钥仅在服务端、鉴权逻辑统一。
        """
        try:
            from services.proxy_service import ProxyService
        except Exception as e:  # noqa: BLE001
            return None, f"无法加载 proxy_service: {type(e).__name__}: {e}"

        lat, lon = coords
        location = f"{lon},{lat}"  # 和风要求 经度,纬度
        try:
            proxy = ProxyService()
            raw = await proxy.qweather("7d", location)
        except Exception as e:  # noqa: BLE001
            return None, f"和风代理调用异常: {type(e).__name__}: {e}"

        if str(raw.get("code")) != "200":
            # 含未配置密钥(401)、host不匹配(403)、网络/HTTP错误(500) 等
            return None, raw.get("message", f"和风返回 code={raw.get('code')}")

        daily = raw.get("daily") or []
        if not daily:
            return None, "和风返回 daily 为空"

        forecasts = self._normalize_qweather_daily(daily, days)
        return {
            "success": True,
            "city": city,
            "forecasts": forecasts,
            "update_time": datetime.now().isoformat(),
            "source": "qweather",
        }, None

    # ---------- Open-Meteo（兜底源） ----------

    async def _fetch_from_open_meteo(self, city: str, days: int, coords: tuple):
        """从 Open-Meteo 获取预报（兜底源）。

        成功返回 source='open-meteo'；任何失败返回 success=False 并附带 warning，
        由上层统一决定最终降级为模拟数据。
        """
        lat, lon = coords
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "weathercode,temperature_2m_max,temperature_2m_min,winddirection_10m_dominant,windspeed_10m_max,relative_humidity_2m_max",
                "timezone": "Asia/Shanghai",
                "forecast_days": min(days, 7),
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.OPEN_METEO_URL, params=params)
                data = response.json()

                daily = data.get("daily", {})
                dates = daily.get("time", [])
                codes = daily.get("weathercode", [])
                temp_maxs = daily.get("temperature_2m_max", [])
                temp_mins = daily.get("temperature_2m_min", [])
                wind_dirs = daily.get("winddirection_10m_dominant", [])
                wind_speeds = daily.get("windspeed_10m_max", [])
                humidities = daily.get("relative_humidity_2m_max", [])

                if not dates:
                    return {"success": False, "warning": "Open-Meteo 返回空 daily"}

                forecasts = []
                for i in range(len(dates)):
                    code = codes[i] if i < len(codes) else 0
                    text_day, text_night = self._wmo_to_text(code)
                    temp_max = temp_maxs[i] if i < len(temp_maxs) else 25
                    temp_min = temp_mins[i] if i < len(temp_mins) else 15
                    wind_dir_deg = wind_dirs[i] if i < len(wind_dirs) else 90
                    wind_speed = wind_speeds[i] if i < len(wind_speeds) else 10
                    humidity = humidities[i] if i < len(humidities) else 60

                    wind_dir_text = self._deg_to_wind_dir(wind_dir_deg)
                    wind_scale = self._speed_to_scale(wind_speed)

                    forecasts.append({
                        "fxDate": dates[i],
                        "textDay": text_day,
                        "textNight": text_night,
                        "tempMax": str(int(temp_max)),
                        "tempMin": str(int(temp_min)),
                        "windDirDay": wind_dir_text,
                        "windScaleDay": str(wind_scale),
                        "humidity": str(int(humidity)),
                    })

                return {
                    "success": True,
                    "city": city,
                    "forecasts": forecasts,
                    "update_time": datetime.now().isoformat(),
                    "source": "open-meteo",
                }
        except Exception as e:
            return {"success": False, "warning": f"Open-Meteo 调用失败: {type(e).__name__}: {e}"}

    # ---------- 统一入口 ----------

    async def get_weather_forecast(self, city: str, days: int = 3) -> dict:
        """获取城市未来 N 天天气预报。

        优先级：和风天气（需配置） > Open-Meteo（兜底） > 季节性模拟数据。
        任何降级都在返回的 `warning` 字段与日志中明确说明原因。
        同时记录各阶段耗时，便于排查慢源。
        """
        _t_total = time.perf_counter()
        coords = await self._resolve_coords(city)
        if not coords:
            # 城市未收录经纬度，无法向任一实时源查询
            _t_mock = time.perf_counter()
            mock = self._generate_mock_weather(city, days)
            mock["warning"] = (
                f"城市「{city}」未收录经纬度，无法查询实时天气，已使用季节性模拟数据（仅供参考）"
            )
            logger.warning("[天气] 城市 %s 无经纬度映射，降级模拟: %s (生成耗时 %.1fms)",
                          city, mock["warning"], self._elapsed_ms(_t_mock))
            logger.debug("[天气] get_weather_forecast 总耗时 %.1fms (源=mock-无经纬度)",
                         self._elapsed_ms(_t_total))
            return mock

        warnings: list = []

        # 1) 优先和风天气
        if settings.QWEATHER_HOST and settings.QWEATHER_KEY:
            _t_qw = time.perf_counter()
            try:
                qw_result, qw_err = await self._fetch_from_qweather(city, days, coords)
                _qw_ms = self._elapsed_ms(_t_qw)
                if qw_result:
                    logger.info("[天气] 使用和风天气成功: city=%s days=%s (耗时 %.1fms)", city, days, _qw_ms)
                    logger.debug("[天气] get_weather_forecast 总耗时 %.1fms (源=qweather)", self._elapsed_ms(_t_total))
                    return qw_result
                warnings.append(f"和风天气不可用（{qw_err}）")
                logger.warning("[天气] 和风天气不可用（%s），降级 Open-Meteo (耗时 %.1fms)", qw_err, _qw_ms)
            except Exception as e:  # noqa: BLE001
                _qw_ms = self._elapsed_ms(_t_qw)
                warnings.append(f"和风天气异常: {type(e).__name__}: {e}")
                logger.warning("[天气] 和风天气异常: %s: %s，降级 Open-Meteo (耗时 %.1fms)", type(e).__name__, e, _qw_ms)
        else:
            warnings.append(
                "和风天气未配置（QWEATHER_HOST / QWEATHER_KEY 缺失），已降级 Open-Meteo"
            )
            logger.info("[天气] 和风天气未配置，降级 Open-Meteo（境外接口，国内网络可能不稳定）")

        # 2) 兜底 Open-Meteo
        _t_om = time.perf_counter()
        om_result = await self._fetch_from_open_meteo(city, days, coords)
        _om_ms = self._elapsed_ms(_t_om)
        if om_result.get("success"):
            if warnings:
                om_result["warning"] = "；".join(warnings) + "（Open-Meteo 为境外接口，国内网络可能不稳定）"
            logger.info("[天气] 使用 Open-Meteo 兜底成功: city=%s (耗时 %.1fms)", city, _om_ms)
            logger.debug("[天气] get_weather_forecast 总耗时 %.1fms (源=open-meteo)", self._elapsed_ms(_t_total))
            return om_result

        warnings.append(om_result.get("warning", "Open-Meteo 调用失败"))

        # 3) 两者均失败 → 模拟数据
        _t_mock = time.perf_counter()
        mock = self._generate_mock_weather(city, days)
        _mock_ms = self._elapsed_ms(_t_mock)
        mock["warning"] = "；".join(warnings) + "；最终使用季节性模拟数据（仅供参考）"
        logger.error("[天气] 和风与 Open-Meteo 均失败，降级模拟: %s (生成耗时 %.1fms)", mock["warning"], _mock_ms)
        logger.debug("[天气] get_weather_forecast 总耗时 %.1fms (源=mock)", self._elapsed_ms(_t_total))
        return mock

    def _deg_to_wind_dir(self, deg: float) -> str:
        """风向角度转中文"""
        dirs = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
        idx = int((deg + 22.5) / 45) % 8
        return dirs[idx]

    def _speed_to_scale(self, speed_kmh: float) -> int:
        """风速 km/h 转风力等级（蒲福风级）"""
        if speed_kmh < 1:
            return 0
        elif speed_kmh < 6:
            return 1
        elif speed_kmh < 12:
            return 2
        elif speed_kmh < 20:
            return 3
        elif speed_kmh < 29:
            return 4
        elif speed_kmh < 39:
            return 5
        elif speed_kmh < 50:
            return 6
        elif speed_kmh < 62:
            return 7
        elif speed_kmh < 75:
            return 8
        else:
            return 9

    def format_weather_for_prompt(self, weather_data: dict) -> str:
        """将天气数据格式化为 AI 可理解的文本。

        source 决定标注：qweather=真实数据不标；open-meteo=标注来源；
        mock=标注模拟数据，避免 AI 把编造值当真。
        """
        if not weather_data.get("success"):
            return ""

        city = weather_data.get("city", "")
        forecasts = weather_data.get("forecasts", [])
        source = weather_data.get("source", "")

        source_label = {
            "qweather": "",
            "open-meteo": "（Open-Meteo 实时）",
            "mock": "（模拟数据，仅供参考）",
        }.get(source, "（未知来源）")

        result = f"\n【实时天气信息 - {city}】{source_label}\n"
        for f in forecasts:
            date = f.get("fxDate", "")
            text_day = f.get("textDay", "")
            text_night = f.get("textNight", "")
            temp_max = f.get("tempMax", "")
            temp_min = f.get("tempMin", "")
            wind_dir = f.get("windDirDay", "")
            wind_scale = f.get("windScaleDay", "")

            result += f"- {date}: {text_day}转{text_night}, {temp_min}~{temp_max}°C, {wind_dir}{wind_scale}级\n"

        if source == "mock":
            result += "\n【注意】以上天气为系统模拟数据，并非真实预报，请明确告知用户仅供参考。\n"

        result += "\n【拥挤度提示】热门景点一般在上午 9-11 点和下午 2-4 点人流量最大，建议避开这些时段。\n"
        return result
