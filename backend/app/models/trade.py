from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text, ForeignKey, func
from app.core.database import Base
from app.core.compat import UUID
import uuid


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, comment="组合名称")
    initial_cash = Column(Numeric(18, 4), default=1_000_000)
    cash = Column(Numeric(18, 4), default=1_000_000)
    status = Column(String(20), default="active", comment="active/closed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(), ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Numeric(12, 4), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(), ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False, comment="buy/sell")
    order_type = Column(String(20), default="market", comment="market/limit")
    price = Column(Numeric(12, 4), nullable=False)
    quantity = Column(Integer, nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    commission = Column(Numeric(12, 4), default=0)
    status = Column(String(20), default="filled", comment="pending/filled/cancelled")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
