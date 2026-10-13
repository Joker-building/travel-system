"""行程管理路由：行程列表CRUD、行程详情、行程节点管理"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.trip import (
    TripCreateRequest,
    TripUpdateRequest,
    TripDetailUpdateRequest,
    AddDayRequest,
    DeleteDayRequest,
)
from services.trip_service import TripService
from utils.deps import get_current_user
from utils.response import success_response, fail_response

router = APIRouter(prefix="/api/trips", tags=["行程管理"])


@router.get("/list")
def get_trip_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户所有行程列表"""
    trips = TripService.get_user_trips(db, current_user.id)
    return success_response(data=trips, message="获取行程列表成功")


@router.post("/create")
def create_trip(
    req: TripCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新行程"""
    result = TripService.create_trip(db, current_user.id, req)
    return success_response(data=result, message="行程创建成功")


@router.get("/detail/{trip_id}")
def get_trip_detail(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取行程详情（含景点信息）"""
    detail = TripService.get_trip_detail(db, trip_id)
    if not detail:
        return fail_response(message="行程不存在")
    # 权限校验
    if detail["user_id"] != current_user.id:
        return fail_response(message="无权查看该行程", code=403)
    return success_response(data=detail, message="获取行程详情成功")


@router.put("/update/{trip_id}")
def update_trip(
    trip_id: int,
    req: TripUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新行程基础信息"""
    result = TripService.update_trip(db, trip_id, req)
    if result["success"]:
        return success_response(message=result["message"])
    return fail_response(message=result["message"])


@router.delete("/delete/{trip_id}")
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除行程（级联删除行程节点）"""
    result = TripService.delete_trip(db, trip_id)
    if result["success"]:
        return success_response(message=result["message"])
    return fail_response(message=result["message"])


# ========== 行程节点管理 ==========

@router.put("/detail/update/{detail_id}")
def update_trip_detail(
    detail_id: int,
    req: TripDetailUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新行程节点（修改游玩时间、备注、预算等）"""
    result = TripService.update_trip_detail(db, detail_id, req)
    if result["success"]:
        return success_response(message=result["message"])
    return fail_response(message=result["message"])


@router.delete("/detail/delete/{detail_id}")
def delete_trip_detail(
    detail_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除行程节点（移除景点）"""
    result = TripService.delete_trip_detail(db, detail_id)
    if result["success"]:
        return success_response(message=result["message"])
    return fail_response(message=result["message"])


@router.post("/day/add")
def add_travel_day(
    req: AddDayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增行程天数"""
    result = TripService.add_travel_day(db, req.trip_id)
    if result["success"]:
        return success_response(
            data={"travel_days": result["travel_days"]}, message=result["message"]
        )
    return fail_response(message=result["message"])


@router.post("/day/delete")
def delete_travel_day(
    req: DeleteDayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除行程天数"""
    result = TripService.delete_travel_day(db, req.trip_id, req.day_num)
    if result["success"]:
        return success_response(
            data={"travel_days": result["travel_days"]}, message=result["message"]
        )
    return fail_response(message=result["message"])
