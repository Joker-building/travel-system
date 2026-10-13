"""聊天会话服务：管理历史会话和消息"""

from datetime import datetime

from sqlalchemy.orm import Session

from models.chat import ChatSession, ChatMessage


class ChatService:
    """聊天会话管理服务"""

    @staticmethod
    def create_session(db: Session, user_id: int, title: str = "新对话") -> dict:
        """创建新会话"""
        session = ChatSession(
            user_id=user_id,
            session_title=title,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return {
            "session_id": session.id,
            "session_title": session.session_title,
        }

    @staticmethod
    def get_user_sessions(db: Session, user_id: int) -> list:
        """获取用户所有会话"""
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.update_time.desc())
            .all()
        )
        return [
            {
                "id": s.id,
                "session_title": s.session_title,
                "create_time": s.create_time.strftime("%Y-%m-%d %H:%M:%S")
                if s.create_time
                else "",
                "update_time": s.update_time.strftime("%Y-%m-%d %H:%M:%S")
                if s.update_time
                else "",
            }
            for s in sessions
        ]

    @staticmethod
    def get_session_messages(db: Session, session_id: int) -> list:
        """获取会话所有消息"""
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.create_time)
            .all()
        )
        return [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "create_time": m.create_time.strftime("%Y-%m-%d %H:%M:%S")
                if m.create_time
                else "",
            }
            for m in messages
        ]

    @staticmethod
    def delete_session(db: Session, session_id: int) -> dict:
        """删除会话"""
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return {"success": False, "message": "会话不存在"}

        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
        db.delete(session)
        db.commit()
        return {"success": True, "message": "会话已删除"}
