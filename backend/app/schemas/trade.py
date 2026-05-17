from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class PortfolioCreate(BaseModel):
    name: str
    initial_cash: float = 1_000_000


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    initial_cash: float
    cash: float
    status: str
    created_at: datetime


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    quantity: int
    avg_cost: float


class OrderCreate(BaseModel):
    symbol: str
    side: str  # buy/sell
    price: float
    quantity: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    side: str
    order_type: str
    price: float
    quantity: int
    amount: float
    commission: float
    status: str
    reason: Optional[str] = None
    created_at: datetime
