"""AI对话相关 Pydantic 模型"""

from typing import Optional, List, Any

from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    """AI对话请求"""

    session_id: Optional[int] = Field(None, description="会话id，为空则创建新会话")
    message: str = Field(..., description="用户消息内容")


class ChatSessionResponse(BaseModel):
    """聊天会话响应"""

    id: int
    user_id: int
    session_title: str
    create_time: str
    update_time: str

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """聊天消息响应"""

    id: int
    session_id: int
    role: str
    content: str
    create_time: str

    class Config:
        from_attributes = True


class AIChatResponse(BaseModel):
    """AI对话响应"""

    response_type: str = Field(..., description="响应类型: itinerary / question_answer")
    session_id: int
    chat_title: Optional[str] = None
    narrative: Optional[str] = None
    answer: Optional[str] = None
    trip_id: Optional[int] = None
    needs_save: Optional[bool] = None
    data: Optional[Any] = None


class SaveItineraryRequest(BaseModel):
    """确认将 AI 生成的计划保存为行程（用户确认后才落库）"""

    data: dict = Field(
        ...,
        description="AI 返回的 itinerary 计划数据（与 /api/ai/chat 的 data 字段一致）",
    )
