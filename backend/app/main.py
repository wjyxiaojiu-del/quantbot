import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.routes import api_router
from app.api.endpoints.ws import manager as ws_manager
from app.api.middleware import RequestLoggingMiddleware, ExceptionHandlerMiddleware

logger = logging.getLogger(__name__)
settings = get_settings()


async def _quote_pusher():
    """后台任务：定时推送实时行情给 WebSocket 订阅者（线程池执行同步 IO）"""
    from app.services.data import get_data_source
    import functools
    ds = get_data_source()
    loop = asyncio.get_event_loop()

    while True:
        try:
            symbols = list(ws_manager.subscriptions.keys())
            if symbols:
                for symbol in symbols:
                    if not ws_manager.subscriptions.get(symbol):
                        continue
                    try:
                        data = await loop.run_in_executor(
                            None, functools.partial(ds.get_realtime_quote, symbol)
                        )
                        if data:
                            await ws_manager.broadcast(symbol, {
                                "symbol": symbol,
                                "data": data,
                                "type": "quote",
                            })
                    except Exception as e:
                        logger.debug(f"推送 {symbol} 行情失败: {e}")
        except Exception as e:
            logger.error(f"行情推送循环异常: {e}")

        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(_quote_pusher())
    yield
    task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}
