"""AI 语音对话路由（基于 Vosk 本地识别）"""

import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.ai_service import AIService
from services.voice_service import VoiceService
from utils.deps import get_current_user
from utils.response import success_response, fail_response

router = APIRouter(prefix="/api/ai/voice", tags=["AI语音对话"])


_voice_svc = VoiceService()


@router.post("/stt")
async def speech_to_text(
    file: UploadFile = File(..., description="WAV 音频文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语音转文字（Vosk 本地识别，无需 API Key）"""
    if not _voice_svc.is_available():
        return fail_response(message="Vosk 语音模型未加载，请运行 download_vosk_model.py")

    content = await file.read()
    text = _voice_svc.stt(content)

    if text:
        return success_response(data={"text": text}, message="语音识别成功")
    return fail_response(message="语音识别失败，请重试")


@router.post("/chat")
async def voice_chat(
    file: UploadFile = File(..., description="WAV 音频文件"),
    session_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语音聊天：语音 -> Vosk识别 -> AI回复

    TTS（文字转语音）在前端用浏览器 speechSynthesis 实现。
    """
    if not _voice_svc.is_available():
        return fail_response(message="Vosk 语音模型未加载，请运行 download_vosk_model.py")

    # 1. 语音转文字
    content = await file.read()
    message = _voice_svc.stt(content)

    if not message:
        return fail_response(message="语音识别失败，请重试")

    # 2. AI 回复
    result = await AIService.chat(db, current_user.id, session_id, message)

    if not result.get("success"):
        return fail_response(message=result.get("message", "AI服务异常"))

    ai_text = result.get("answer") or result.get("narrative", "")
    result["recognized_text"] = message

    return success_response(data=result, message="AI语音回复成功")


@router.get("/status")
async def voice_status(
    current_user: User = Depends(get_current_user),
):
    """检查语音服务状态"""
    return success_response(
        data={"available": _voice_svc.is_available()},
        message="语音服务可用" if _voice_svc.is_available() else "语音服务不可用"
    )
