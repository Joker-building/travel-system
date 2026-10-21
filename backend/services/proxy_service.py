"""第三方 API 代理服务

将所有第三方密钥（和风天气 / 高德地图 / 百度翻译）收敛到服务端，
前端只与本服务的 /api/proxy/* 交互，避免密钥落入客户端代码或被小程序包提取。
"""

import hashlib
import random
import string

import httpx

from config import settings


# 和风天气支持的子接口白名单（防止被当作开放代理滥用）
# 注：空气质量(air)已由和风废弃(v7/air/now 返回 403 Deprecated)，
# 改走免密钥的 Open-Meteo 空气质量接口，见 air_quality()。
_QWEATHER_ENDPOINTS = {
    "now": "v7/weather/now",
    "7d": "v7/weather/7d",
    "24h": "v7/weather/24h",
    "indices": "v7/indices/1d",
}


class ProxyService:
    """第三方 API 代理（密钥仅在服务端）"""

    # ---------- 和风天气 ----------
    async def qweather(self, endpoint: str, location: str, type_: str = "0") -> dict:
        """代理和风天气接口，返回其原始 JSON。

        endpoint: now | 7d | 24h | indices（空气质量见 air_quality，不走和风）
        location: 经纬度，形如 "116.41,39.92"
        """
        path = _QWEATHER_ENDPOINTS.get(endpoint)
        if not path:
            return {"code": "400", "message": f"不支持的天气接口: {endpoint}"}
        if not settings.QWEATHER_HOST or not settings.QWEATHER_KEY:
            return {"code": "401", "message": "服务端未配置和风天气密钥"}

        params = {"location": location, "key": settings.QWEATHER_KEY}
        if endpoint == "indices":
            params["type"] = type_

        url = f"https://{settings.QWEATHER_HOST}/{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 401:
                    # Key 失效/被重置/过期——配置问题，给出可执行提示。
                    return {
                        "code": "401",
                        "message": (
                            "和风天气鉴权失败(HTTP 401)：API Key 可能已在和风控制台"
                            "失效/被重置/过期。请到 console.qweather.com 进入项目"
                            f"「{settings.QWEATHER_HOST}」重新复制一个有效 Key，"
                            "写入 backend/.env 的 QWEATHER_KEY 后重启后端。"
                        ),
                    }
                if resp.status_code == 403:
                    body = (resp.text or "").lower()
                    if "deprecated" in body:
                        # 接口已被和风废弃（如 v7/air/now），不是密钥问题。
                        return {
                            "code": "403",
                            "message": (
                                f"和风天气接口 {path} 已被官方废弃(Deprecated)，"
                                "请改用对应的新版本接口。"
                            ),
                        }
                    # 其余 403 多为 host 与订阅不匹配。
                    return {
                        "code": "403",
                        "message": (
                            "和风天气返回 HTTP 403(Invalid Host)：当前 QWEATHER_HOST"
                            f"「{settings.QWEATHER_HOST}」与该 Key 所属订阅不匹配。"
                            "请到 console.qweather.com 复制与此 Key 同一项目的 API Host 写入 QWEATHER_HOST。"
                        ),
                    }
                if resp.status_code != 200:
                    return {
                        "code": str(resp.status_code),
                        "message": f"和风天气请求失败(HTTP {resp.status_code})",
                    }
                data = resp.json()
                # 和风天气成功时 code == "200"
                if str(data.get("code")) != "200":
                    return {
                        "code": str(data.get("code", "unknown")),
                        "message": data.get("summary") or data.get("message") or "和风天气返回错误",
                    }
                return data
        except Exception as e:  # noqa: BLE001
            return {"code": "500", "message": f"和风天气请求失败: {e}"}

    async def qweather_geo(self, city: str) -> dict:
        """代理和风地理编码（城市名 -> 经纬度），返回原始 JSON。

        与天气 API 同属一个订阅，复用 QWEATHER_KEY。兼容两种订阅形态：

        - 标准订阅：Geo 与天气同主机，路径为 ``/geo/v2/city/lookup``
          （如 ``https://<host>/geo/v2/city/lookup``）；
        - 免费开发者版：Geo 为独立主机 ``geoapi.qweather.com``，路径 ``/v2/city/lookup``。

        为避免用户手动配错 ``QWEATHER_GEO_HOST`` 导致 404，这里按候选列表依次尝试，
        命中第一个返回 ``code==200`` 且含 ``location`` 的地址即返回；全部失败才降级。
        成功时 location[0] 含 lat/lon。
        """
        if not settings.QWEATHER_HOST or not settings.QWEATHER_KEY:
            return {"code": "401", "message": "服务端未配置和风天气密钥"}
        params = {"location": city, "key": settings.QWEATHER_KEY, "number": 1}

        # 候选地址：标准订阅(同主机 /geo/v2) 优先，开发者版(独立主机 /v2) 兜底。
        candidates: list[str] = []
        if settings.QWEATHER_GEO_HOST and settings.QWEATHER_GEO_HOST != "geoapi.qweather.com":
            # 用户显式配置了非默认 geo 主机，优先使用
            candidates.append(f"https://{settings.QWEATHER_GEO_HOST}/v2/city/lookup")
        candidates.append(f"https://{settings.QWEATHER_HOST}/geo/v2/city/lookup")
        candidates.append("https://geoapi.qweather.com/v2/city/lookup")

        last_err = None
        for url in candidates:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code} @ {url}"
                    continue
                data = resp.json()
                if str(data.get("code")) == "200" and (data.get("location") or []):
                    return data
                # code 非 200 或无结果：记下来，尝试下一个候选
                last_err = f"code={data.get('code')} {data.get('message') or ''} @ {url}"
            except Exception as e:  # noqa: BLE001
                last_err = f"{type(e).__name__}: {e} @ {url}"
        return {"code": "404", "message": f"和风地理编码请求失败（全部候选失败）: {last_err}"}

    # ---------- 空气质量（Open-Meteo，免密钥） ----------
    async def air_quality(self, location: str) -> dict:
        """根据经纬度获取空气质量（AQI）。

        和风原 v7/air/now 接口已于 2025 年废弃(返回 403 Deprecated)，
        这里改用完全免费、无需 Key 的 Open-Meteo 空气质量接口，
        并映射成与和风 air/now 兼容的 {code, now:{aqi,category,...}} 结构。
        location: 经纬度，形如 "116.41,39.92"（经度在前，Open-Meteo 需要拆开）。
        """
        try:
            lon, lat = (part.strip() for part in location.split(",", 1))
        except Exception:  # noqa: BLE001
            return {"code": "400", "message": "经纬度格式错误，应为 经度,纬度"}

        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "us_aqi,pm2_5,pm10,ozone,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide",
            "timezone": "Asia/Shanghai",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            return {"code": "500", "message": f"空气质量请求失败: {e}"}

        cur = data.get("current") or {}
        if not cur or cur.get("us_aqi") is None:
            return {"code": "204", "message": "暂无空气质量数据"}

        aqi = int(round(float(cur.get("us_aqi"))))
        level, category = self._aqi_level(aqi)
        return {
            "code": "200",
            "now": {
                "aqi": str(aqi),
                "level": str(level),
                "category": category,
                "primary": "PM2.5" if (float(cur.get("pm2_5") or 0)) >= (float(cur.get("pm10") or 0)) else "PM10",
                "pm2p5": str(cur.get("pm2_5")),
                "pm10": str(cur.get("pm10")),
                "o3": str(cur.get("ozone")),
                "co": str(cur.get("carbon_monoxide")),
                "no2": str(cur.get("nitrogen_dioxide")),
                "so2": str(cur.get("sulphur_dioxide")),
            },
        }

    @staticmethod
    def _aqi_level(aqi: int) -> tuple:
        """按美国 AQI 标准映射等级与描述（与和风 category 语义对齐）。"""
        if aqi <= 50:
            return 1, "优"
        if aqi <= 100:
            return 2, "良"
        if aqi <= 150:
            return 3, "轻度污染"
        if aqi <= 200:
            return 4, "中度污染"
        if aqi <= 300:
            return 5, "重度污染"
        return 6, "严重污染"

    # ---------- 高德地图（逆地理编码） ----------
    async def amap_regeo(self, location: str) -> dict:
        """根据经纬度解析城市名称。

        location: 经纬度，形如 "116.41,39.92"
        返回 {"city": "武汉市"} 或 {"city": None}
        """
        if not settings.AMAP_KEY:
            return {"city": None, "message": "服务端未配置高德地图密钥"}

        url = "https://restapi.amap.com/v3/geocode/regeo"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    url,
                    params={"location": location, "key": settings.AMAP_KEY, "extensions": "base"},
                )
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            return {"city": None, "message": f"高德地图请求失败: {e}"}

        if data.get("status") != "1":
            return {"city": None, "message": data.get("info", "逆地理编码失败")}

        addr = (data.get("regeocode") or {}).get("addressComponent") or {}
        # 直辖市 city 可能为空，回退到 province
        city = addr.get("city") or addr.get("province")
        return {"city": city}

    # ---------- 百度翻译 ----------
    async def baidu_translate(self, q: str, from_lang: str = "auto", to_lang: str = "zh") -> dict:
        """代理百度翻译，返回 {"text": "译文"}。签名在服务端用密钥计算。"""
        if not settings.BAIDU_TRANSLATE_APPID or not settings.BAIDU_TRANSLATE_KEY:
            return {"text": None, "message": "服务端未配置百度翻译密钥"}

        salt = "".join(random.choices(string.digits, k=8))
        sign_raw = settings.BAIDU_TRANSLATE_APPID + q + salt + settings.BAIDU_TRANSLATE_KEY
        sign = hashlib.md5(sign_raw.encode("utf-8")).hexdigest()

        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        params = {
            "q": q,
            "from": from_lang,
            "to": to_lang,
            "appid": settings.BAIDU_TRANSLATE_APPID,
            "salt": salt,
            "sign": sign,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            return {"text": None, "message": f"百度翻译请求失败: {e}"}

        if data.get("error_code"):
            return {"text": None, "message": f"{data.get('error_code')}: {data.get('error_msg')}"}

        trans = data.get("trans_result") or []
        if not trans:
            return {"text": None, "message": "翻译结果为空"}
        return {"text": trans[0].get("dst", "")}
