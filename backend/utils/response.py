"""统一响应封装"""

from fastapi.responses import JSONResponse


def success_response(data=None, message: str = "操作成功", code: int = 200):
    """成功响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def fail_response(message: str = "操作失败", code: int = 400, data=None):
    """失败响应

    返回带正确 HTTP 状态码的 JSONResponse，
    避免业务失败被 FastAPI 默认当成 200。
    """
    return JSONResponse(
        status_code=code,
        content={
            "code": code,
            "message": message,
            "data": data,
        },
    )
