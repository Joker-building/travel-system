"""第三方 API 代理路由

前端不再直连和风天气 / 高德 / 百度翻译，而是调用本路由；
所有第三方密钥仅在服务端（backend/.env）保存，避免泄露。
"""

from fastapi import APIRouter, Depends, Query

from services.proxy_service import ProxyService
from utils.deps import get_current_user_optional
from utils.response import success_response, fail_response

router = APIRouter(prefix="/api/proxy", tags=["第三方API代理"])

_proxy = ProxyService()


@router.get("/weather")
async def proxy_weather(
    endpoint: str = Query(..., description="now | 7d | 24h | indices | air"),
    location: str = Query(..., description="经纬度，形如 116.41,39.92"),
    type: str = Query("0", description="indices 接口的天气指数类型"),
    _user=Depends(get_current_user_optional),
):
    """代理天气/空气质量接口。

    now/7d/24h/indices 走和风天气；air(空气质量)走免密钥的 Open-Meteo。
    """
    if endpoint == "air":
        result = await _proxy.air_quality(location)
    else:
        result = await _proxy.qweather(endpoint, location, type)

    if result.get("code") != "200":
        return fail_response(message=result.get("message", "请求失败"), code=int(result.get("code", 400)))
    return success_response(data=result, message="获取成功")


@router.get("/regeo")
async def proxy_regeo(
    location: str = Query(..., description="经纬度，形如 116.41,39.92"),
    _user=Depends(get_current_user_optional),
):
    """根据经纬度解析城市名称。"""
    result = await _proxy.amap_regeo(location)
    if result.get("city") is None:
        return fail_response(message=result.get("message", "解析失败"), code=400)
    return success_response(data=result, message="获取成功")


@router.get("/translate")
async def proxy_translate(
    q: str = Query(..., description="待翻译文本"),
    from_lang: str = Query("auto", description="源语言"),
    to_lang: str = Query("zh", description="目标语言"),
    _user=Depends(get_current_user_optional),
):
    """代理百度翻译，返回译文文本。"""
    result = await _proxy.baidu_translate(q, from_lang, to_lang)
    if result.get("text") is None:
        return fail_response(message=result.get("message", "翻译失败"), code=400)
    return success_response(data=result, message="翻译成功")
