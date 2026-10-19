"""应用配置模块"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """全局配置"""

    # 数据库类型: sqlite / mysql
    DB_TYPE: str = os.getenv("DB_TYPE", "mysql")

    # MySQL 数据库
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "travel_system")

    # SQLite 数据库文件路径
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "travel_system.db")

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            return f"sqlite:///{self.SQLITE_PATH}"
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "travel-system-secret-key-2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )

    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL: str = os.getenv(
        "DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"
    )
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # ===== 纯 Langchain + pgvector（RAG 检索层）配置 =====
    # 总开关：False 时完全走原逻辑，保证已完成的工程不受任何影响（默认关闭）
    USE_RAG: bool = os.getenv("USE_RAG", "False").lower() == "true"

    # 意图路由总开关：开启后用 LLM 三意图分类（daily_qa / knowledge / plan）决定
    # 是否使用知识库（仅 knowledge 进 RAG，daily_qa 大模型直答，plan 走行程规划）；
    # 关闭时回退旧的二元逻辑（非 plan 全部进 RAG），保证可灰度、可回滚（默认开启）。
    INTENT_ROUTER_ENABLED: bool = os.getenv("INTENT_ROUTER_ENABLED", "True").lower() == "true"

    # Embedding 后端：默认 ollama（本机已用 Ollama 部署 bge-m3，ollama list 可见
    # bge-m3:latest，维度 1024；纯本地、零联网，且无需 sentence-transformers/torch）。
    # 如需改回本地 sentence-transformers，设 RAG_EMBED_BACKEND=hf 并安装
    # langchain-huggingface + sentence-transformers。
    RAG_EMBED_BACKEND: str = os.getenv("RAG_EMBED_BACKEND", "ollama")
    # HF 模型名（仅 backend=hf 时生效）
    RAG_EMBED_MODEL: str = os.getenv("RAG_EMBED_MODEL", "BAAI/bge-m3")
    # Ollama 模型名与地址（backend=ollama 时生效）
    RAG_OLLAMA_MODEL: str = os.getenv("RAG_OLLAMA_MODEL", "bge-m3")
    RAG_OLLAMA_BASE_URL: str = os.getenv("RAG_OLLAMA_BASE_URL", "http://localhost:11434")

    # 每次语义检索召回的候选条数
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))

    # PostgreSQL / pgvector 连接（本机已安装 PostgreSQL 17，pgvector 扩展已手动启用）
    # 连接目标：本机 PostgreSQL @ localhost:5432，库 vector_db，超级用户 postgres
    RAG_PG_HOST: str = os.getenv("RAG_PG_HOST", "localhost")
    RAG_PG_PORT: int = int(os.getenv("RAG_PG_PORT", "5432"))
    RAG_PG_USER: str = os.getenv("RAG_PG_USER", "postgres")
    RAG_PG_PASSWORD: str = os.getenv("RAG_PG_PASSWORD", "123456")
    RAG_PG_DB: str = os.getenv("RAG_PG_DB", "vector_db")
    # Langchain PGVector 在 vector_db 内使用的集合名（自动建表 langchain_pg_collection / langchain_pg_embedding）
    # 统一集合：scenic_spot 景点本体 + knowledge_doc 知识库语料，靠 doc_type 元数据区分。
    RAG_PG_COLLECTION: str = os.getenv("RAG_PG_COLLECTION", "travel_kb")

    @property
    def RAG_PG_CONNECTION_STRING(self) -> str:
        # langchain-postgres（1.x 中 PGVector 的归属包）使用 psycopg3 驱动，
        # 连接串必须是 postgresql+psycopg://...（注意：不是 psycopg2）
        return (
            f"postgresql+psycopg://{self.RAG_PG_USER}:{self.RAG_PG_PASSWORD}"
            f"@{self.RAG_PG_HOST}:{self.RAG_PG_PORT}/{self.RAG_PG_DB}"
        )

    # 百度语音 API（语音识别 STT 备用配置；当前 Vosk 本地识别无需 Key）
    BAIDU_ASR_API_KEY: str = os.getenv("BAIDU_ASR_API_KEY", "")
    BAIDU_ASR_SECRET_KEY: str = os.getenv("BAIDU_ASR_SECRET_KEY", "")

    # 和风天气 API（前端天气数据经后端 /api/proxy/weather 代理，密钥仅在服务端保存）
    QWEATHER_HOST: str = os.getenv("QWEATHER_HOST", "")
    QWEATHER_KEY: str = os.getenv("QWEATHER_KEY", "")
    QWEATHER_API_URL: str = os.getenv("QWEATHER_API_URL", "https://devapi.qweather.com/v7")
    QWEATHER_JWT_TOKEN: str = os.getenv("QWEATHER_JWT_TOKEN", "")

    # 高德地图 API（前端逆地理编码经后端 /api/proxy/regeo 代理）
    AMAP_KEY: str = os.getenv("AMAP_KEY", "")

    # 百度翻译 API（前端翻译经后端 /api/proxy/translate 代理，签名在服务端计算）
    BAIDU_TRANSLATE_APPID: str = os.getenv("BAIDU_TRANSLATE_APPID", "")
    BAIDU_TRANSLATE_KEY: str = os.getenv("BAIDU_TRANSLATE_KEY", "")

    # 文件上传
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "1048576"))  # 1MB

    # 应用
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() == "true"


settings = Settings()
