"""AI辅助行程规划路由：景点搜索、AI搜索景点、AI获取景点详情、添加景点到行程"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.scenic_spot import (
    ScenicSpotSearchRequest,
    AISearchScenicRequest,
    AddScenicToTripRequest,
    ScenicDetailRequest,
)
from schemas.ai import SaveItineraryRequest
from services.scenic_service import ScenicService
from services.ai_service import AIService
from utils.deps import get_current_user
from utils.response import success_response, fail_response

router = APIRouter(prefix="/api/planning", tags=["AI辅助规划"])


@router.get("/scenic/search")
def search_scenic(
    keyword: str,
    city: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索景点（数据库匹配 name 和 address 字段）"""
    spots = ScenicService.search_scenic_spots(db, keyword, city)
    return success_response(data=spots, message="搜索完成")


@router.post("/scenic/ai-search")
async def ai_search_scenic(
    req: AISearchScenicRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI搜索景点（高德式）：返回多个候选景点卡片，前端挑选后再通过 add-to-trip 加入行程"""
    result = await AIService.search_scenic(req.keyword, req.city)
    if result.get("success"):
        return success_response(data=result, message="AI搜索完成，返回候选景点列表")
    return fail_response(message=result.get("message", "AI搜索失败"))


@router.post("/scenic/add-to-trip")
def add_scenic_to_trip(
    req: AddScenicToTripRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将已有景点添加到行程"""
    result = ScenicService.add_scenic_to_trip(db, req.scenic_id, req.trip_id, req.day_num)
    if result["success"]:
        return success_response(data=result, message=result["message"])
    return fail_response(message=result["message"])


@router.post("/scenic/ai-detail")
async def get_scenic_ai_detail(
    req: ScenicDetailRequest,
    current_user: User = Depends(get_current_user),
):
    """AI获取景点详细信息（景区介绍、门票、注意事项、预算规划）"""
    result = await AIService.get_scenic_detail(req.scenic_name, req.city)
    if result.get("success"):
        return success_response(data=result["detail"], message="获取景点详情成功")
    return fail_response(message=result.get("message", "获取详情失败"))


@router.get("/scenic/{scenic_id}")
def get_scenic_info(
    scenic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据ID获取景点信息"""
    scenic = ScenicService.get_scenic_by_id(db, scenic_id)
    if scenic:
        return success_response(data=scenic, message="获取景点信息成功")
    return fail_response(message="景点不存在")


@router.post("/itinerary/save")
def save_itinerary(
    req: SaveItineraryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将 AI 生成的计划保存为行程（用户在前端点「添加到行程」后调用）

    不再在对话阶段自动落库，避免用户放弃的计划产生孤儿 trip / scenic 记录。
    """
    trip_id = AIService._process_itinerary(db, current_user.id, req.data)
    if trip_id:
        return success_response(data={"trip_id": trip_id}, message="行程已添加")
    return fail_response(message="保存行程失败，请稍后重试")
