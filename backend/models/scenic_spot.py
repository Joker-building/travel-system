"""景点信息模型"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, Text

from database import Base


class ScenicSpot(Base):
    """景点信息表"""

    __tablename__ = "scenic_spot"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="景点id")
    name = Column(String(100), nullable=False, comment="景点名称")
    city = Column(String(50), nullable=False, index=True, comment="所属城市")
    introduction = Column(Text, comment="简介")
    address = Column(String(255), default="", comment="地址")
    open_time = Column(String(100), default="", comment="开放时间")
    price = Column(Float, default=0, comment="门票价格")
    latitude = Column(Float, comment="纬度")
    longitude = Column(Float, comment="经度")
    special_notice = Column(String(500), default="", comment="特殊提醒/注意事项")
    suggested_duration = Column(String(50), default="", comment="建议游玩时长")
    # 高德式扩展字段
    category = Column(String(50), default="", comment="分类标签，如自然风光/历史古迹/主题乐园")
    rating = Column(Float, default=0.0, comment="评分0-5")
    tel = Column(String(50), default="", comment="咨询电话")
    tags = Column(Text, default="", comment="标签，JSON数组字符串")
    recommendation = Column(Text, default="", comment="推荐理由")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
