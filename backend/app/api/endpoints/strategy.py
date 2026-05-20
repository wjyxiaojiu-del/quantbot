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


@router.get("", response_model=List[StrategyBrief])
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


@router.post("", response_model=StrategyOut, status_code=201)
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


@router.post("/optimize")
async def optimize_strategy_params(data: dict, db: Session = Depends(get_db)):
    """网格搜索最优策略参数
    请求体：
    {
        "strategy_code": "...",
        "symbol": "000001.SZ",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "initial_cash": 1000000,
        "param_grid": {
            "short_window": [5, 10, 15],
            "long_window": [20, 30, 50]
        },
        "optimize_by": "sharpe_ratio",  // sharpe_ratio | total_return | win_rate
        "top_n": 5
    }
    """
    from itertools import product
    from app.services.backtest.engine import BacktestEngine
    from datetime import date as date_type

    strategy_code = data.get("strategy_code", "")
    symbol = data.get("symbol", "")
    start_date_str = data.get("start_date", "")
    end_date_str = data.get("end_date", "")
    initial_cash = data.get("initial_cash", 1_000_000)
    param_grid = data.get("param_grid", {})
    optimize_by = data.get("optimize_by", "sharpe_ratio")
    top_n = data.get("top_n", 5)

    if not strategy_code or not symbol:
        raise HTTPException(status_code=400, detail="缺少 strategy_code 或 symbol")

    # 加载 K 线数据
    start_date = date_type.fromisoformat(start_date_str) if start_date_str else date_type(2023, 1, 1)
    end_date = date_type.fromisoformat(end_date_str) if end_date_str else date_type.today()

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
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的 K 线数据")

    df = pd.DataFrame([{
        "symbol": r.symbol, "trade_date": str(r.trade_date),
        "open": float(r.open), "high": float(r.high),
        "low": float(r.low), "close": float(r.close),
        "volume": int(r.volume),
    } for r in rows])

    # 生成参数组合
    if not param_grid:
        raise HTTPException(status_code=400, detail="param_grid 不能为空")

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(product(*values))

    if len(combinations) > 500:
        raise HTTPException(status_code=400, detail=f"参数组合数 {len(combinations)} 超过上限 500")

    # 遍历回测
    results = []
    for combo in combinations:
        params = dict(zip(keys, combo))
        try:
            engine = BacktestEngine(initial_cash=initial_cash)
            result = engine.run(strategy_code, df.copy(), params)
            if result["status"] == "completed":
                metrics = result["metrics"]
                results.append({
                    "params": params,
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                    "total_return": metrics.get("total_return", 0),
                    "annual_return": metrics.get("annual_return", 0),
                    "max_drawdown": metrics.get("max_drawdown", 0),
                    "win_rate": metrics.get("win_rate", 0),
                    "trade_count": metrics.get("trade_count", 0),
                    "profit_loss_ratio": metrics.get("profit_loss_ratio", 0),
                })
        except Exception:
            continue

    if not results:
        return {"results": [], "message": "所有参数组合均执行失败"}

    # 排序
    valid_keys = {"sharpe_ratio", "total_return", "annual_return", "win_rate", "profit_loss_ratio"}
    sort_key = optimize_by if optimize_by in valid_keys else "sharpe_ratio"
    results.sort(key=lambda x: x[sort_key], reverse=True)

    return {
        "total_combinations": len(combinations),
        "successful": len(results),
        "optimize_by": sort_key,
        "results": results[:top_n],
    }
