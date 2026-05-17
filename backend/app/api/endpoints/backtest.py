from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.models.kline import StockDailyKline
from app.models.backtest import BacktestResult
from app.schemas.backtest import BacktestRequest, BacktestResultOut
from app.services.backtest.engine import BacktestEngine

import pandas as pd

router = APIRouter()


def _load_kline_df(db: Session, symbol: str, start_date, end_date) -> pd.DataFrame:
    rows = (
        db.query(StockDailyKline)
        .filter(
            StockDailyKline.symbol == symbol,
            StockDailyKline.trade_date >= start_date,
            StockDailyKline.trade_date <= end_date,
        )
        .order_by(StockDailyKline.trade_date)
        .all()
    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([
        {
            "symbol": r.symbol,
            "trade_date": str(r.trade_date),
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": int(r.volume),
        }
        for r in rows
    ])


@router.post("/run", response_model=BacktestResultOut)
async def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    """执行回测（支持多股票）"""
    kline_dict = {}
    for symbol in req.symbols:
        df = _load_kline_df(db, symbol, req.start_date, req.end_date)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 在指定区间内的 K 线数据")
        kline_dict[symbol] = df

    engine = BacktestEngine(initial_cash=req.initial_cash)

    if len(req.symbols) == 1:
        result = engine.run(req.strategy_code, list(kline_dict.values())[0], req.params)
    else:
        result = engine.run_multi(req.strategy_code, kline_dict, req.params)

    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["error"])

    # 保存结果
    record = BacktestResult(
        strategy_id="manual",
        name=f"{'、'.join(req.symbols)} 回测",
        start_date=req.start_date,
        end_date=req.end_date,
        symbols=req.symbols,
        initial_cash=req.initial_cash,
        params=req.params,
        total_return=result["metrics"]["total_return"],
        annual_return=result["metrics"]["annual_return"],
        sharpe_ratio=result["metrics"]["sharpe_ratio"],
        max_drawdown=result["metrics"]["max_drawdown"],
        volatility=result["metrics"]["volatility"],
        win_rate=result["metrics"]["win_rate"],
        profit_loss_ratio=result["metrics"]["profit_loss_ratio"],
        trade_count=result["metrics"]["trade_count"],
        daily_pnl=[],
        trades=result["trades"],
        equity_curve=result["equity_curve"],
        status="completed",
    )
    db.add(record)
    db.commit()

    return BacktestResultOut(
        status="completed",
        metrics=result["metrics"],
        equity_curve=result["equity_curve"],
        trades=result["trades"],
    )


@router.get("/history")
async def list_backtest_history(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(BacktestResult).order_by(BacktestResult.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "symbols": r.symbols,
                "total_return": float(r.total_return) if r.total_return else None,
                "sharpe_ratio": float(r.sharpe_ratio) if r.sharpe_ratio else None,
                "max_drawdown": float(r.max_drawdown) if r.max_drawdown else None,
                "trade_count": r.trade_count,
                "status": r.status,
                "created_at": str(r.created_at),
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{backtest_id}")
async def get_backtest_detail(backtest_id: UUID, db: Session = Depends(get_db)):
    record = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="回测记录不存在")
    return {
        "id": str(record.id),
        "name": record.name,
        "symbols": record.symbols,
        "start_date": str(record.start_date),
        "end_date": str(record.end_date),
        "initial_cash": float(record.initial_cash),
        "params": record.params,
        "total_return": float(record.total_return) if record.total_return else None,
        "annual_return": float(record.annual_return) if record.annual_return else None,
        "sharpe_ratio": float(record.sharpe_ratio) if record.sharpe_ratio else None,
        "max_drawdown": float(record.max_drawdown) if record.max_drawdown else None,
        "volatility": float(record.volatility) if record.volatility else None,
        "win_rate": float(record.win_rate) if record.win_rate else None,
        "profit_loss_ratio": float(record.profit_loss_ratio) if record.profit_loss_ratio else None,
        "trade_count": record.trade_count,
        "equity_curve": record.equity_curve,
        "trades": record.trades,
        "status": record.status,
        "created_at": str(record.created_at),
    }
