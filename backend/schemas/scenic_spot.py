"""景点相关 Pydantic 模型"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScenicSpotResponse(BaseModel):
    """景点信息响应（高德式：含分类/评分/电话/标签/推荐理由）"""

    id: int
    name: str
    city: str
    category: Optional[str] = ""
    introduction: Optional[str]
    address: str
    open_time: str
    price: float
    rating: float = 0
    latitude: Optional[float]
    longitude: Optional[float]
    tel: Optional[str] = ""
    tags: list = []
    special_notice: str
    suggested_duration: str
    recommendation: Optional[str] = ""
    create_time: datetime

    class Config:
        from_attributes = True


class ScenicSpotSearchRequest(BaseModel):
    """景点搜索请求"""

    keyword: str = Field(..., description="搜索关键词")
    city: str = Field(default="", description="城市")


class AISearchScenicRequest(BaseModel):
    """AI搜索景点请求（高德式：返回候选列表，挑选后再通过 add-to-trip 加入行程）"""

    keyword: str = Field(..., description="搜索关键词")
    city: str = Field(..., description="所属城市")
    trip_id: Optional[int] = Field(default=None, description="可选：行程id（历史兼容，新接口不再自动加入）")
    day_num: Optional[int] = Field(default=None, description="可选：第几天（历史兼容）")


class AddScenicToTripRequest(BaseModel):
    """添加景点到行程请求"""

    scenic_id: int = Field(..., description="景点id")
    trip_id: int = Field(..., description="行程id")
    day_num: int = Field(default=1, description="第几天")


class ScenicDetailRequest(BaseModel):
    """获取AI景点详情请求"""

    scenic_name: str = Field(..., description="景点名称")
    city: str = Field(..., description="所在城市")
