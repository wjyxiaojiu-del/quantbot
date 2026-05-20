import time
import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = round((time.time() - start) * 1000, 1)
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed}ms)")
        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常捕获中间件"""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(f"Unhandled error: {request.method} {request.url.path}")

            settings = get_settings()
            if settings.DEBUG:
                # DEBUG 模式返回详细错误信息
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": str(e),
                        "type": type(e).__name__,
                        "traceback": traceback.format_exc(),
                    },
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "服务器内部错误，请稍后重试"},
                )
