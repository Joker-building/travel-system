"""天气路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.weather_service import WeatherService
from utils.deps import get_current_user
from utils.response import success_response, fail_response

router = APIRouter(prefix="/api/weather", tags=["天气服务"])


@router.get("/forecast")
async def get_weather_forecast(
    city: str,
    days: int = 3,
    current_user: User = Depends(get_current_user),
):
    """获取城市天气预报（基于 Open-Meteo，无需 Key；失败自动降级为模拟数据）"""
    weather_svc = WeatherService()
    result = await weather_svc.get_weather_forecast(city, days)

    if result.get("success"):
        source = result.get("source", "unknown")
        msg = "获取天气成功（模拟数据）" if source == "mock" else "获取天气成功"
        return success_response(data=result, message=msg)
    return fail_response(message=result.get("message", "获取天气失败"))
