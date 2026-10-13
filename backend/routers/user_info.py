"""用户信息管理路由：查看/修改个人信息、头像上传、退出登录"""

import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import UserUpdateRequest
from utils.deps import get_current_user
from utils.response import success_response, fail_response
from config import settings

router = APIRouter(prefix="/api/user", tags=["用户信息管理"])

# 允许的图片格式
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}


@router.get("/info")
def get_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return success_response(
        data={
            "id": current_user.id,
            "username": current_user.username,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
            "city": current_user.city,
            "gender": current_user.gender,
            "phone": current_user.phone,
            "create_time": current_user.create_time.strftime("%Y-%m-%d %H:%M:%S")
            if current_user.create_time
            else "",
        },
        message="获取用户信息成功",
    )


@router.put("/update")
def update_user_info(
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改用户信息（昵称、城市、性别、电话等）"""
    if req.nickname is not None:
        current_user.nickname = req.nickname
    if req.city is not None:
        current_user.city = req.city
    if req.gender is not None:
        current_user.gender = req.gender
    if req.phone is not None:
        current_user.phone = req.phone
    if req.avatar_url is not None:
        current_user.avatar_url = req.avatar_url

    from datetime import datetime

    current_user.update_time = datetime.now()
    db.commit()
    db.refresh(current_user)

    return success_response(
        data={
            "id": current_user.id,
            "username": current_user.username,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
            "city": current_user.city,
            "gender": current_user.gender,
            "phone": current_user.phone,
        },
        message="用户信息更新成功",
    )


@router.post("/avatar/upload")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传用户头像"""
    # 校验文件格式
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return fail_response(message="仅支持 jpg、png、gif 格式的图片")

    # 校验文件大小
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        return fail_response(message="文件大小不能超过1MB")

    # 生成唯一文件名
    unique_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_name)

    # 写入文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 生成可访问的 URL
    avatar_url = f"/uploads/avatars/{unique_name}"

    # 更新数据库
    from datetime import datetime

    current_user.avatar_url = avatar_url
    current_user.update_time = datetime.now()
    db.commit()

    return success_response(
        data={"avatar_url": avatar_url},
        message="头像上传成功",
    )


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
):
    """退出登录（前端清除本地token，后端确认）"""
    return success_response(message="退出登录成功")
