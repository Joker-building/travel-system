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

    # 对话历史管控（修剪硬限 + 摘要软压缩，对应 Langchain 记忆课件）
    HISTORY_MAX_PAIRS: int = int(os.getenv("HISTORY_MAX_PAIRS", "12"))      # 最近保留 N 个 (user,assistant) 配对
    HISTORY_MAX_TOKENS: int = int(os.getenv("HISTORY_MAX_TOKENS", "6000"))  # 历史 token 硬上限（DeepSeek 32k 窗口 ~19%）
    SUMMARY_TRIGGER_PAIRS: int = int(os.getenv("SUMMARY_TRIGGER_PAIRS", "8"))  # 窗口外累计达此数才重算摘要
    SUMMARY_MAX_TOKENS: int = int(os.getenv("SUMMARY_MAX_TOKENS", "400"))  # 摘要目标长度


settings = Settings()
