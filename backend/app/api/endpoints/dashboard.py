from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.stock import Stock
from app.models.kline import StockDailyKline
from app.models.strategy import Strategy
from app.models.backtest import BacktestResult
from app.models.trade import Portfolio, Position, Order

router = APIRouter()


@router.get("/")
async def get_dashboard(db: Session = Depends(get_db)):
    """首页 Dashboard 数据聚合"""
    # 股票统计
    stock_count = db.query(Stock).count()
    kline_count = db.query(StockDailyKline).count()

    # 最近同步的股票
    latest_kline = (
        db.query(StockDailyKline.symbol, func.max(StockDailyKline.trade_date))
        .group_by(StockDailyKline.symbol)
        .order_by(func.max(StockDailyKline.trade_date).desc())
        .limit(5)
        .all()
    )

    # 策略统计
    strategy_count = db.query(Strategy).count()
    active_strategies = db.query(Strategy).filter(Strategy.status == "active").count()

    # 回测统计
    backtest_count = db.query(BacktestResult).count()
    best_backtest = (
        db.query(BacktestResult)
        .filter(BacktestResult.status == "completed")
        .order_by(BacktestResult.total_return.desc())
        .first()
    )

    # 交易组合
    portfolios = db.query(Portfolio).all()
    portfolio_summaries = []
    total_cash = 0
    total_equity = 0
    for p in portfolios:
        positions = db.query(func.sum(Position.quantity * Position.avg_cost)).filter(
            Position.portfolio_id == p.id, Position.quantity > 0
        ).scalar() or 0
        equity = float(p.cash) + float(positions)
        total_cash += float(p.cash)
        total_equity += equity
        portfolio_summaries.append({
            "id": str(p.id),
            "name": p.name,
            "equity": round(equity, 2),
            "return_pct": round((equity - float(p.initial_cash)) / float(p.initial_cash) * 100, 2),
        })

    # 最近交易
    recent_orders = (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "market": {
            "stock_count": stock_count,
            "kline_count": kline_count,
            "latest_synced": [{"symbol": s[0], "date": str(s[1])} for s in latest_kline],
        },
        "strategy": {
            "total": strategy_count,
            "active": active_strategies,
        },
        "backtest": {
            "total": backtest_count,
            "best_return": float(best_backtest.total_return) if best_backtest else None,
            "best_name": best_backtest.name if best_backtest else None,
        },
        "portfolio": {
            "count": len(portfolios),
            "total_cash": round(total_cash, 2),
            "total_equity": round(total_equity, 2),
            "items": portfolio_summaries,
        },
        "recent_orders": [
            {
                "id": str(o.id),
                "symbol": o.symbol,
                "side": o.side,
                "price": float(o.price),
                "quantity": o.quantity,
                "created_at": str(o.created_at),
            }
            for o in recent_orders
        ],
    }
