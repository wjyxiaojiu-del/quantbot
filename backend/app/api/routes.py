from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.api.endpoints import market, strategy, backtest, trade, auth, templates, ws, dashboard

api_router = APIRouter()

# ── 公开端点（无需认证）──
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

# ── 受保护端点（需认证）──
api_router.include_router(
    dashboard.router, prefix="/dashboard", tags=["dashboard"],
    dependencies=[Depends(get_current_user)]
)
api_router.include_router(
    market.router, prefix="/market", tags=["market"],
    dependencies=[Depends(get_current_user)]
)
api_router.include_router(
    strategy.router, prefix="/strategies", tags=["strategies"],
    dependencies=[Depends(get_current_user)]
)
api_router.include_router(
    backtest.router, prefix="/backtest", tags=["backtest"],
    dependencies=[Depends(get_current_user)]
)
api_router.include_router(
    trade.router, prefix="/trade", tags=["trade"],
    dependencies=[Depends(get_current_user)]
)
