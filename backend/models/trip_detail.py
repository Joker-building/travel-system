"""行程节点信息模型"""

from datetime import datetime, time

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Time
from sqlalchemy.orm import relationship

from database import Base


class TripDetail(Base):
    """行程节点信息表"""

    __tablename__ = "trip_detail"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="行程节点id")
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="CASCADE"), nullable=False, index=True, comment="行程id")
    scenic_id = Column(Integer, ForeignKey("scenic_spot.id", ondelete="SET NULL"), nullable=True, index=True, comment="景点id")
    start_time = Column(Time, comment="开始时间")
    end_time = Column(Time, comment="结束时间")
    remark = Column(String(500), default="", comment="备注")
    day_num = Column(Integer, default=1, comment="行程天数序号（第几天）")
    sort_order = Column(Integer, default=0, comment="当日内排序序号")
    spot_budget = Column(Float, default=0, comment="景点预算")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联关系
    scenic_spot = relationship("ScenicSpot", backref="trip_details")
