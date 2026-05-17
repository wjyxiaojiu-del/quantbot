from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    exchange: str
    industry: Optional[str] = None
    list_date: Optional[date] = None
    status: str = "active"


class KLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    change_pct: Optional[Decimal] = None
    turnover: Optional[Decimal] = None


class SyncRequest(BaseModel):
    symbols: Optional[List[str]] = None
    period: str = "daily"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SyncResponse(BaseModel):
    success: bool
    total: int
    success_count: int
    failed_count: int
    errors: List[str] = []
