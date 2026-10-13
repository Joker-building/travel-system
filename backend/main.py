"""
AI辅助个性化旅游行程定制系统 - 后端主程序
=====================================
技术栈: Python + FastAPI + MySQL + SQLAlchemy + DeepSeek AI
"""

import os
import sys

# 强制 UTF-8 编码，防止在 PyCharm 等 IDE 中出现中文乱码
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import engine, Base
from routers import auth, trips, ai_chat, ai_planning, user_info, ai_voice, weather, proxy

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI辅助个性化旅游行程定制系统",
    description="基于 FastAPI + DeepSeek 的个性化旅游行程定制后端服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务 - 用于访问上传的头像
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 注册路由
app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(ai_chat.router)
app.include_router(ai_planning.router)
app.include_router(user_info.router)
app.include_router(ai_voice.router)
app.include_router(weather.router)
app.include_router(proxy.router)


@app.get("/")
def root():
    """根路径"""
    return {
        "system": "AI辅助个性化旅游行程定制系统",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
