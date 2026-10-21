"""聊天会话与消息模型"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from database import Base


class ChatSession(Base):
    """聊天会话表"""

    __tablename__ = "chat_session"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话id")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户id")
    session_title = Column(String(100), default="新对话", comment="会话标题")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    summary = Column(Text, nullable=True, comment="较早对话的 LLM 摘要(软压缩缓存)")

    # 关联关系
    messages = relationship(
        "ChatMessage",
        backref="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.create_time",
    )


class ChatMessage(Base):
    """聊天消息表"""

    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息id")
    session_id = Column(Integer, ForeignKey("chat_session.id", ondelete="CASCADE"), nullable=False, index=True, comment="会话id")
    role = Column(String(20), nullable=False, comment="角色: system/user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
