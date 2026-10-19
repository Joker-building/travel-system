"""数据库连接与会话管理"""

# 注：SQLAlchemy 2.0.36 在 uvicorn 热重载（watchfiles / spawn 子进程）下存在 C 扩展
# 循环导入崩溃（cyextension.util -> exc -> util.compat）的已知 bug，已在 2.0.37+ 修复。
# 本项目已升级到 2.0.41，无需再设置 DISABLE_SQLALCHEMY_CEXT_RUNTIME 绕过，保留此说明以便回溯。

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=settings.APP_DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
