"""行程信息模型"""

from datetime import datetime, date

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from database import Base


class Trip(Base):
    """行程信息表"""

    __tablename__ = "trip"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="行程id")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户id")
    trip_name = Column(String(100), nullable=False, comment="行程标题")
    dest_city = Column(String(50), nullable=False, comment="目的地城市")
    start_date = Column(Date, comment="行程开始时间")
    end_date = Column(Date, comment="行程结束时间")
    total_budget = Column(Float, default=0, comment="预算")
    travel_days = Column(Integer, default=1, comment="旅行天数")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    # 关联关系
    details = relationship(
        "TripDetail",
        backref="trip",
        cascade="all, delete-orphan",
        order_by="TripDetail.day_num, TripDetail.sort_order",
    )
