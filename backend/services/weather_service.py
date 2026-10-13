"""天气服务：基于 Open-Meteo 获取城市天气预报

Open-Meteo 是完全免费、无需注册、无需 API Key 的天气 API。
支持全球城市（通过经纬度查询），返回 WMO 天气代码，自动映射为中文。
"""

import json
import random
import httpx
from typing import Optional
from datetime import datetime, timedelta


class WeatherService:
    """Open-Meteo 天气服务（完全免费，无需 Key）"""

    # 城市经纬度映射（用于 Open-Meteo 查询）
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

    # Open-Meteo API 地址（完全免费，无需 Key）
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    # 各季节典型天气（用于降级模拟）
    SEASONAL_WEATHER = {
        "spring": [("晴", "多云", 15, 25), ("多云", "小雨", 12, 22), ("晴", "晴", 18, 28)],
        "summer": [("晴", "多云", 26, 35), ("雷阵雨", "多云", 25, 33), ("晴", "晴", 28, 38)],
        "autumn": [("晴", "晴", 15, 25), ("多云", "晴", 12, 22), ("小雨", "多云", 10, 20)],
        "winter": [("多云", "阴", 0, 10), ("晴", "晴", -2, 8), ("小雪", "多云", -5, 3)],
    }

    def __init__(self, api_key: str = "", api_url: str = "", jwt_token: str = ""):
        # 兼容旧配置，Open-Meteo 不需要 Key
        pass

    def _get_coords(self, city: str) -> Optional[tuple]:
        """获取城市的经纬度"""
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
        """生成季节性模拟天气数据（降级方案）"""
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

    async def get_weather_forecast(self, city: str, days: int = 3) -> dict:
        """获取城市未来 N 天的天气预报

        使用 Open-Meteo API（完全免费，无需 Key）。
        失败时自动降级为季节性模拟数据。
        """
        coords = self._get_coords(city)
        if not coords:
            return self._generate_mock_weather(city, days)

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
                    return self._generate_mock_weather(city, days)

                forecasts = []
                for i in range(len(dates)):
                    code = codes[i] if i < len(codes) else 0
                    text_day, text_night = self._wmo_to_text(code)
                    temp_max = temp_maxs[i] if i < len(temp_maxs) else 25
                    temp_min = temp_mins[i] if i < len(temp_mins) else 15
                    wind_dir_deg = wind_dirs[i] if i < len(wind_dirs) else 90
                    wind_speed = wind_speeds[i] if i < len(wind_speeds) else 10
                    humidity = humidities[i] if i < len(humidities) else 60

                    # 风向角度转中文
                    wind_dir_text = self._deg_to_wind_dir(wind_dir_deg)
                    # 风速 km/h 转风力等级
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
            print(f"[天气] Open-Meteo 调用失败: {e}，降级为模拟数据")
            return self._generate_mock_weather(city, days)

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
        """将天气数据格式化为 AI 可理解的文本"""
        if not weather_data.get("success"):
            return ""

        city = weather_data.get("city", "")
        forecasts = weather_data.get("forecasts", [])
        source = weather_data.get("source", "")

        source_label = "（模拟数据）" if source == "mock" else ""
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

        result += "\n【拥挤度提示】热门景点一般在上午 9-11 点和下午 2-4 点人流量最大，建议避开这些时段。\n"
        return result
