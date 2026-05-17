from sqlalchemy import Column, String, Date, DateTime, Numeric, Integer, Text, JSON, func
from app.core.database import Base
from app.core.compat import UUID
import uuid


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    
    # 回测参数
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    symbols = Column(JSON, nullable=False, default=list)
    initial_cash = Column(Numeric(18, 4), default=1_000_000)
    params = Column(JSON, default=dict)
    
    # 绩效指标
    total_return = Column(Numeric(10, 4), nullable=True)
    annual_return = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    max_drawdown = Column(Numeric(10, 4), nullable=True)
    max_drawdown_period = Column(Integer, nullable=True)
    volatility = Column(Numeric(10, 4), nullable=True)
    win_rate = Column(Numeric(6, 4), nullable=True)
    profit_loss_ratio = Column(Numeric(10, 4), nullable=True)
    trade_count = Column(Integer, nullable=True)
    
    # 详细结果
    daily_pnl = Column(JSON, default=list)
    trades = Column(JSON, default=list)
    equity_curve = Column(JSON, default=list)
    
    status = Column(String(20), default="running")  # running/completed/failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
