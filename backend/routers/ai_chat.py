"""AI对话路由：AI智能行程生成、智能问答、会话管理"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.ai import AIChatRequest
from services.ai_service import AIService
from services.chat_service import ChatService
from utils.deps import get_current_user
from utils.response import success_response, fail_response

router = APIRouter(prefix="/api/ai", tags=["AI对话"])


@router.post("/chat")
async def ai_chat(
    req: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI对话主接口：智能行程生成 / 智能问答"""
    result = await AIService.chat(db, current_user.id, req.session_id, req.message)
    if result.get("success"):
        return success_response(data=result, message="AI响应成功")
    return fail_response(message=result.get("message", "AI服务异常"))


@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户所有历史会话列表"""
    sessions = ChatService.get_user_sessions(db, current_user.id)
    return success_response(data=sessions, message="获取会话列表成功")


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定会话的所有消息记录"""
    messages = ChatService.get_session_messages(db, session_id)
    return success_response(data=messages, message="获取消息记录成功")


@router.post("/sessions/create")
def create_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    title: str = "新对话",
):
    """创建新会话"""
    result = ChatService.create_session(db, current_user.id, title)
    return success_response(data=result, message="会话创建成功")


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话"""
    result = ChatService.delete_session(db, session_id)
    if result["success"]:
        return success_response(message=result["message"])
    return fail_response(message=result["message"])
