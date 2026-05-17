import logging
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import pandas as pd

from app.services.data import get_data_source
from app.models.stock import Stock
from app.models.kline import StockDailyKline

logger = logging.getLogger(__name__)


class DataSyncManager:
    """数据同步管理器 — 批量 upsert 优化"""

    def __init__(self, db: Session):
        self.db = db
        self.ds = get_data_source()

    def get_all_stock_symbols(self) -> List[str]:
        stocks = self.db.query(Stock.symbol).filter(Stock.status == "active").all()
        return [s[0] for s in stocks]

    async def sync_stock_list(self) -> int:
        logger.info("开始同步股票列表...")
        df = self.ds.fetch_stock_list()
        if df.empty:
            return 0

        # 批量查询已有 symbol
        existing_rows = self.db.query(Stock.symbol, Stock.name, Stock.exchange).all()
        existing = {r[0]: r for r in existing_rows}
        existing_symbols = set(existing.keys())

        new_count = 0
        update_count = 0

        # 分离新增和更新
        new_stocks = []
        for _, row in df.iterrows():
            sym = row["symbol"]
            if sym in existing_symbols:
                # 名称或交易所有变化才更新
                old = existing[sym]
                if old[1] != row["name"] or old[2] != row["exchange"]:
                    update_count += 1
                    self.db.query(Stock).filter(Stock.symbol == sym).update(
                        {"name": row["name"], "exchange": row["exchange"]}
                    )
            else:
                new_stocks.append({
                    "symbol": sym,
                    "name": row["name"],
                    "exchange": row["exchange"],
                    "status": "active",
                })
                new_count += 1

        # 批量插入新股票
        if new_stocks:
            batch_size = 500
            for i in range(0, len(new_stocks), batch_size):
                batch = new_stocks[i : i + batch_size]
                self.db.bulk_insert_mappings(Stock, batch)

        self.db.commit()
        logger.info(f"股票列表同步完成: 新增 {new_count}, 更新 {update_count}")
        return new_count

    async def sync_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        if not start_date:
            last = (
                self.db.query(StockDailyKline.trade_date)
                .filter(StockDailyKline.symbol == symbol)
                .order_by(StockDailyKline.trade_date.desc())
                .first()
            )
            start_date = (last[0] + timedelta(days=1)) if last else date(2010, 1, 1)

        if not end_date:
            end_date = date.today()

        if start_date > end_date:
            return {"symbol": symbol, "inserted": 0, "message": "已是最新数据"}

        try:
            df = self.ds.fetch_kline(symbol, period, start_date, end_date)
        except Exception as e:
            logger.error(f"同步 {symbol} 失败: {e}")
            return {"symbol": symbol, "inserted": 0, "error": str(e)}

        if df.empty:
            return {"symbol": symbol, "inserted": 0, "message": "无数据"}

        # 批量查询已有日期，避免逐条 SELECT
        existing_dates = set(
            r[0]
            for r in self.db.query(StockDailyKline.trade_date)
            .filter(
                StockDailyKline.symbol == symbol,
                StockDailyKline.trade_date >= start_date,
                StockDailyKline.trade_date <= end_date,
            )
            .all()
        )

        # 批量构建新记录
        new_rows = []
        for _, row in df.iterrows():
            if row["trade_date"] not in existing_dates:
                new_rows.append({
                    "symbol": row["symbol"],
                    "trade_date": row["trade_date"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": int(row["volume"]),
                    "amount": row["amount"],
                    "change_pct": row.get("change_pct"),
                    "turnover": row.get("turnover"),
                })

        # 批量插入
        if new_rows:
            # 分批插入，每批 500 条
            batch_size = 500
            for i in range(0, len(new_rows), batch_size):
                batch = new_rows[i : i + batch_size]
                self.db.bulk_insert_mappings(StockDailyKline, batch)
            self.db.commit()

        logger.info(f"同步 {symbol} 完成: 插入 {len(new_rows)} 条")
        return {"symbol": symbol, "inserted": len(new_rows)}

    async def sync_kline_batch(
        self,
        symbols: List[str],
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        success_count = 0
        failed_count = 0
        errors = []

        for symbol in symbols:
            try:
                result = await self.sync_kline(symbol, period, start_date, end_date)
                if "error" not in result:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"{symbol}: {result['error']}")
            except Exception as e:
                failed_count += 1
                errors.append(f"{symbol}: {str(e)}")

        return {
            "success": failed_count == 0,
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors[:10],
        }
