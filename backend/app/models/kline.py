from sqlalchemy import Column, String, Date, DateTime, Numeric, BigInteger, PrimaryKeyConstraint, CheckConstraint, func
from app.core.database import Base


class StockDailyKline(Base):
    __tablename__ = "stock_daily_kline"

    symbol = Column(String(20), nullable=False, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    open = Column(Numeric(12, 4), nullable=False)
    high = Column(Numeric(12, 4), nullable=False)
    low = Column(Numeric(12, 4), nullable=False)
    close = Column(Numeric(12, 4), nullable=False)
    volume = Column(BigInteger, nullable=False, comment="成交量（股）")
    amount = Column(Numeric(18, 4), nullable=False, comment="成交额（元）")
    change_pct = Column(Numeric(8, 4), nullable=True, comment="涨跌幅 %")
    turnover = Column(Numeric(8, 4), nullable=True, comment="换手率 %")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("symbol", "trade_date"),
        CheckConstraint("high >= low AND high >= close AND high >= open", name="chk_daily_price"),
    )

    def __repr__(self):
        return f"<DailyK({self.symbol} {self.trade_date})>"


class StockMinuteKline(Base):
    __tablename__ = "stock_minute_kline"

    symbol = Column(String(20), nullable=False)
    trade_time = Column(DateTime, nullable=False)
    period = Column(String(10), nullable=False, comment="1m/5m/15m/30m/60m")
    open = Column(Numeric(12, 4), nullable=False)
    high = Column(Numeric(12, 4), nullable=False)
    low = Column(Numeric(12, 4), nullable=False)
    close = Column(Numeric(12, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("symbol", "trade_time", "period"),
    )

    def __repr__(self):
        return f"<MinuteK({self.symbol} {self.trade_time} {self.period})>"
