"""用户相关 Pydantic 模型"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserRegisterRequest(BaseModel):
    """用户注册请求"""

    username: str = Field(..., max_length=16, min_length=1, description="用户名")
    password: str = Field(..., max_length=16, min_length=1, description="密码")
    confirm_password: str = Field(..., max_length=16, min_length=1, description="确认密码")
    nickname: str = Field(..., max_length=10, min_length=1, description="昵称")
    city: str = Field(default="", max_length=50, description="常住城市")


class UserLoginRequest(BaseModel):
    """用户登录请求"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""

    nickname: Optional[str] = Field(None, max_length=10, description="昵称")
    city: Optional[str] = Field(None, max_length=50, description="常住城市")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像url")


class UserResponse(BaseModel):
    """用户信息响应"""

    id: int
    username: str
    nickname: str
    avatar_url: str
    city: str
    gender: str
    phone: str
    create_time: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """登录令牌响应"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
