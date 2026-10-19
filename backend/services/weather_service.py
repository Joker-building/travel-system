"""天气服务：和风天气优先，Open-Meteo 兜底

数据来源策略（三级）：
1. 优先使用和风天气（国内服务，稳定；需配置 QWEATHER_HOST + QWEATHER_KEY，密钥仅服务端）；
2. 和风未配置或调用失败时，降级使用 Open-Meteo（境外免费接口，无需 Key，但国内网络可能不稳定）；
3. 两者均失败时，降级为季节性模拟数据。

任何降级都会在返回 dict 的 `warning` 字段与日志中给出明确提示，便于排障。
"""

import random
import time
import httpx
from typing import Optional
from datetime import datetime, timedelta

from config import settings


class WeatherService:
    """天气服务：和风优先，Open-Meteo 兜底"""

    # 城市经纬度映射（用于经纬度查询；和风与 Open-Meteo 都需要）
    CITY_COORDS = {
        "武汉": (30.59, 114.31),
        "北京": (39.90, 116.40),
        "上海": (31.23, 121.47),
        "广州": (23.13, 113.27),
        "深圳": (22.54, 114.06),
        "成都": (30.67, 104.07),
        "杭州": (30.27, 120.15),
        "西安": (34.27, 108.95),
        "重庆": (29.56, 106.55),
        "南京": (32.04, 118.78),
        "长沙": (28.23, 112.94),
        "厦门": (24.48, 118.09),
        "青岛": (36.07, 120.38),
        "三亚": (18.25, 109.51),
        "恩施": (30.27, 109.49),
        "宜昌": (30.71, 111.29),
        "张家界": (29.12, 110.48),
        "桂林": (25.27, 110.29),
        "昆明": (25.04, 102.71),
        "大理": (25.69, 100.16),
        "丽江": (26.87, 100.22),
        "香格里拉": (27.83, 99.71),
        "拉萨": (29.65, 91.11),
        "黄山": (30.08, 118.31),
        "庐山": (29.55, 115.99),
        "岳阳": (29.36, 113.13),
        "凤凰": (27.95, 109.60),
        "阳朔": (24.74, 110.29),
        "北海": (21.48, 109.12),
    }

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

    def _get_coords(self, city: str) -> Optional[tuple]:
        """获取城市的经纬度 (lat, lon)"""
        return self.CITY_COORDS.get(city)

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
        coords = self._get_coords(city)
        if not coords:
            # 城市未收录经纬度，无法向任一实时源查询
            _t_mock = time.perf_counter()
            mock = self._generate_mock_weather(city, days)
            mock["warning"] = (
                f"城市「{city}」未收录经纬度，无法查询实时天气，已使用季节性模拟数据（仅供参考）"
            )
            print(f"[天气] 城市 {city} 无经纬度映射，降级模拟: {mock['warning']} "
                  f"(生成耗时 {self._elapsed_ms(_t_mock):.1f}ms)")
            print(f"[天气] get_weather_forecast 总耗时 {self._elapsed_ms(_t_total):.1f}ms (源=mock-无经纬度)")
            return mock

        warnings: list = []

        # 1) 优先和风天气
        if settings.QWEATHER_HOST and settings.QWEATHER_KEY:
            _t_qw = time.perf_counter()
            try:
                qw_result, qw_err = await self._fetch_from_qweather(city, days, coords)
                _qw_ms = self._elapsed_ms(_t_qw)
                if qw_result:
                    print(f"[天气] 使用和风天气成功: city={city} days={days} (耗时 {_qw_ms:.1f}ms)")
                    print(f"[天气] get_weather_forecast 总耗时 {self._elapsed_ms(_t_total):.1f}ms (源=qweather)")
                    return qw_result
                warnings.append(f"和风天气不可用（{qw_err}）")
                print(f"[天气] 和风天气不可用（{qw_err}），降级 Open-Meteo (耗时 {_qw_ms:.1f}ms)")
            except Exception as e:  # noqa: BLE001
                _qw_ms = self._elapsed_ms(_t_qw)
                warnings.append(f"和风天气异常: {type(e).__name__}: {e}")
                print(f"[天气] 和风天气异常: {type(e).__name__}: {e}，降级 Open-Meteo (耗时 {_qw_ms:.1f}ms)")
        else:
            warnings.append(
                "和风天气未配置（QWEATHER_HOST / QWEATHER_KEY 缺失），已降级 Open-Meteo"
            )
            print("[天气] 和风天气未配置，降级 Open-Meteo（境外接口，国内网络可能不稳定）")

        # 2) 兜底 Open-Meteo
        _t_om = time.perf_counter()
        om_result = await self._fetch_from_open_meteo(city, days, coords)
        _om_ms = self._elapsed_ms(_t_om)
        if om_result.get("success"):
            if warnings:
                om_result["warning"] = "；".join(warnings) + "（Open-Meteo 为境外接口，国内网络可能不稳定）"
            print(f"[天气] 使用 Open-Meteo 兜底成功: city={city} (耗时 {_om_ms:.1f}ms)")
            print(f"[天气] get_weather_forecast 总耗时 {self._elapsed_ms(_t_total):.1f}ms (源=open-meteo)")
            return om_result

        warnings.append(om_result.get("warning", "Open-Meteo 调用失败"))

        # 3) 两者均失败 → 模拟数据
        _t_mock = time.perf_counter()
        mock = self._generate_mock_weather(city, days)
        _mock_ms = self._elapsed_ms(_t_mock)
        mock["warning"] = "；".join(warnings) + "；最终使用季节性模拟数据（仅供参考）"
        print(f"[天气] 和风与 Open-Meteo 均失败，降级模拟: {mock['warning']} (生成耗时 {_mock_ms:.1f}ms)")
        print(f"[天气] get_weather_forecast 总耗时 {self._elapsed_ms(_t_total):.1f}ms (源=mock)")
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
