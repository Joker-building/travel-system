"""认证服务：用户注册、登录"""

from datetime import datetime

from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserRegisterRequest, UserLoginRequest
from utils.security import hash_password, verify_password, create_access_token


class AuthService:
    """认证服务"""

    @staticmethod
    def register(db: Session, req: UserRegisterRequest) -> dict:
        """用户注册"""
        # 校验两次密码是否一致
        if req.password != req.confirm_password:
            return {"success": False, "message": "两次输入的密码不一致"}

        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == req.username).first()
        if existing_user:
            return {"success": False, "message": "用户名已被注册"}

        # 创建用户，密码使用 PBKDF2-SHA256 加密
        user = User(
            username=req.username,
            password=hash_password(req.password),
            nickname=req.nickname,
            city=req.city,
            avatar_url="",
            gender="",
            phone="",
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": "注册成功",
            "user_id": user.id,
            "username": user.username,
        }

    @staticmethod
    def login(db: Session, req: UserLoginRequest) -> dict:
        """用户登录"""
        user = db.query(User).filter(User.username == req.username).first()
        if not user:
            return {"success": False, "message": "用户名不存在"}

        if not verify_password(req.password, user.password):
            return {"success": False, "message": "密码错误"}

        # 生成 JWT token
        token = create_access_token({"sub": str(user.id)})

        # 更新最后登录时间
        user.update_time = datetime.now()
        db.commit()

        return {
            "success": True,
            "message": "登录成功",
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
                "city": user.city,
                "gender": user.gender,
                "phone": user.phone,
                "create_time": user.create_time.strftime("%Y-%m-%d %H:%M:%S")
                if user.create_time
                else "",
            },
        }
