from fastapi import APIRouter

from app.api.endpoints import market, strategy, backtest, trade, auth, templates, ws, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(strategy.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(trade.router, prefix="/trade", tags=["trade"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
