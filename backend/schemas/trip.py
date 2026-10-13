"""行程相关 Pydantic 模型"""

from datetime import date, datetime, time
from typing import Optional, List

from pydantic import BaseModel, Field


class TripCreateRequest(BaseModel):
    """创建行程请求"""

    trip_name: str = Field(..., max_length=100, description="行程标题")
    dest_city: str = Field(..., max_length=50, description="目的地城市")
    start_date: Optional[date] = Field(None, description="行程开始时间")
    end_date: Optional[date] = Field(None, description="行程结束时间")
    total_budget: float = Field(default=0, description="预算")


class TripUpdateRequest(BaseModel):
    """更新行程请求"""

    trip_name: Optional[str] = Field(None, max_length=100, description="行程标题")
    dest_city: Optional[str] = Field(None, max_length=50, description="目的地城市")
    start_date: Optional[date] = Field(None, description="行程开始时间")
    end_date: Optional[date] = Field(None, description="行程结束时间")
    total_budget: Optional[float] = Field(None, description="预算")


class TripResponse(BaseModel):
    """行程信息响应"""

    id: int
    user_id: int
    trip_name: str
    dest_city: str
    start_date: Optional[date]
    end_date: Optional[date]
    total_budget: float
    travel_days: int
    create_time: datetime
    status: Optional[str] = None

    class Config:
        from_attributes = True


class TripDetailResponse(BaseModel):
    """行程节点响应"""

    id: int
    trip_id: int
    scenic_id: Optional[int]
    start_time: Optional[time]
    end_time: Optional[time]
    remark: str
    day_num: int
    sort_order: int
    spot_budget: float
    scenic_spot: Optional[dict] = None

    class Config:
        from_attributes = True


class TripDetailUpdateRequest(BaseModel):
    """更新行程节点请求"""

    start_time: Optional[time] = None
    end_time: Optional[time] = None
    remark: Optional[str] = Field(None, max_length=500)
    spot_budget: Optional[float] = None
    sort_order: Optional[int] = None
    day_num: Optional[int] = None


class AddDayRequest(BaseModel):
    """新增行程天数请求"""

    trip_id: int


class DeleteDayRequest(BaseModel):
    """删除行程天数请求"""

    trip_id: int
    day_num: int
