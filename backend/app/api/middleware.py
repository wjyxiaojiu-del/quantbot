import time
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

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
            return JSONResponse(
                status_code=500,
                content={"detail": "服务器内部错误，请稍后重试"},
            )
