"""用户信息模型"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from database import Base


class User(Base):
    """用户信息表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户id")
    username = Column(String(16), unique=True, nullable=False, index=True, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码（加密存储）")
    nickname = Column(String(10), nullable=False, comment="昵称")
    avatar_url = Column(String(500), default="", comment="头像url")
    city = Column(String(50), default="", comment="常住城市")
    gender = Column(String(10), default="", comment="性别")
    phone = Column(String(20), default="", comment="联系电话")
    create_time = Column(DateTime, default=datetime.now, comment="注册时间")
    update_time = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
