from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.core.database import get_db
from app.models.strategy import Strategy
from app.models.kline import StockDailyKline
from app.schemas.strategy import StrategyCreate, StrategyUpdate, StrategyOut, StrategyBrief
from app.services.strategy.executor import StrategyExecutor
import pandas as pd

router = APIRouter()


@router.get("/", response_model=List[StrategyBrief])
async def list_strategies(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Strategy)
    if status:
        query = query.filter(Strategy.status == status)
    query = query.order_by(Strategy.updated_at.desc())
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy(strategy_id: UUID, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    return strategy


@router.post("/", response_model=StrategyOut, status_code=201)
async def create_strategy(data: StrategyCreate, db: Session = Depends(get_db)):
    existing = db.query(Strategy).filter(Strategy.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="策略名称已存在")
    strategy = Strategy(**data.model_dump())
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.put("/{strategy_id}", response_model=StrategyOut)
async def update_strategy(strategy_id: UUID, data: StrategyUpdate, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(strategy, key, value)
    strategy.version += 1
    db.commit()
    db.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(strategy_id: UUID, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    db.delete(strategy)
    db.commit()


@router.post("/{strategy_id}/execute")
async def execute_strategy(
    strategy_id: UUID,
    symbol: str = Query(..., description="股票代码"),
    period: str = Query("daily"),
    days: int = Query(250, ge=30, le=2000, description="回看天数"),
    db: Session = Depends(get_db),
):
    """对指定股票执行策略，生成信号"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    from datetime import timedelta
    end = date.today()
    start = end - timedelta(days=days)

    rows = (
        db.query(StockDailyKline)
        .filter(
            StockDailyKline.symbol == symbol,
            StockDailyKline.trade_date >= start,
            StockDailyKline.trade_date <= end,
        )
        .order_by(StockDailyKline.trade_date)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的 K 线数据")

    df = pd.DataFrame([{
        "symbol": r.symbol, "trade_date": str(r.trade_date),
        "open": float(r.open), "high": float(r.high),
        "low": float(r.low), "close": float(r.close),
        "volume": int(r.volume),
    } for r in rows])

    result = StrategyExecutor.generate_signals(strategy.code, df, strategy.params)
    return result


@router.post("/validate")
async def validate_strategy_code(data: dict):
    """验证策略代码是否合法"""
    code = data.get("code", "")
    valid, msg = StrategyExecutor.validate_code(code)
    return {"valid": valid, "message": msg}
