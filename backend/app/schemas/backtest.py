from pydantic import BaseModel
from datetime import date
from typing import Optional, Dict, Any, List
from uuid import UUID


class BacktestRequest(BaseModel):
    strategy_code: str
    symbols: List[str]
    start_date: date
    end_date: date
    initial_cash: float = 1_000_000
    params: Optional[Dict[str, Any]] = {}


class BacktestResultOut(BaseModel):
    status: str
    metrics: Optional[Dict[str, Any]] = None
    equity_curve: Optional[List[dict]] = None
    trades: Optional[List[dict]] = None
    error: Optional[str] = None
