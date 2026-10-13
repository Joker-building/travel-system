"""认证路由：用户注册、登录"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from schemas.user import UserRegisterRequest, UserLoginRequest
from services.auth_service import AuthService
from utils.response import success_response, fail_response

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register")
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    result = AuthService.register(db, req)
    if result["success"]:
        return success_response(
            data={"user_id": result["user_id"], "username": result["username"]},
            message=result["message"],
        )
    return fail_response(message=result["message"])


@router.post("/login")
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    result = AuthService.login(db, req)
    if result["success"]:
        return success_response(
            data={
                "access_token": result["token"],
                "token_type": "bearer",
                "user": result["user"],
            },
            message=result["message"],
        )
    return fail_response(message=result["message"])
