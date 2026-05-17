from sqlalchemy import Column, String, Date, DateTime, func
from app.core.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    symbol = Column(String(20), primary_key=True, comment="股票代码如 000001.SZ")
    name = Column(String(100), nullable=False, comment="股票名称")
    exchange = Column(String(10), nullable=False, comment="交易所 SZ/SH/BJ")
    industry = Column(String(50), nullable=True, comment="所属行业")
    list_date = Column(Date, nullable=True, comment="上市日期")
    status = Column(String(20), default="active", comment="active/suspended/delisted")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Stock({self.symbol} {self.name})>"
