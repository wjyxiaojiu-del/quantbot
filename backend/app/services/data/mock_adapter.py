"""
模拟数据源 — 用于开发测试、API 限流时的降级方案
生成逼真的 A 股模拟 K 线数据
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Optional
import random

from app.services.data.base import BaseDataSource

# 常见 A 股股票列表
_STOCK_LIST = [
    ("000001.SZ", "平安银行", "SZ"), ("000002.SZ", "万科A", "SZ"),
    ("000063.SZ", "中兴通讯", "SZ"), ("000333.SZ", "美的集团", "SZ"),
    ("000651.SZ", "格力电器", "SZ"), ("000725.SZ", "京东方A", "SZ"),
    ("000858.SZ", "五粮液", "SZ"), ("002230.SZ", "科大讯飞", "SZ"),
    ("002415.SZ", "海康威视", "SZ"), ("002594.SZ", "比亚迪", "SZ"),
    ("300059.SZ", "东方财富", "SZ"), ("300750.SZ", "宁德时代", "SZ"),
    ("600000.SH", "浦发银行", "SH"), ("600009.SH", "上海机场", "SH"),
    ("600016.SH", "民生银行", "SH"), ("600028.SH", "中国石化", "SH"),
    ("600030.SH", "中信证券", "SH"), ("600036.SH", "招商银行", "SH"),
    ("600048.SH", "保利发展", "SH"), ("600050.SH", "中国联通", "SH"),
    ("600276.SH", "恒瑞医药", "SH"), ("600309.SH", "万华化学", "SH"),
    ("600519.SH", "贵州茅台", "SH"), ("600585.SH", "海螺水泥", "SH"),
    ("600887.SH", "伊利股份", "SH"), ("601012.SH", "隆基绿能", "SH"),
    ("601088.SH", "中国神华", "SH"), ("601318.SH", "中国平安", "SH"),
    ("601398.SH", "工商银行", "SH"), ("601857.SH", "中国石油", "SH"),
    ("601899.SH", "紫金矿业", "SH"), ("603259.SH", "药明康德", "SH"),
]


class MockDataSource(BaseDataSource):
    """模拟数据源"""

    def __init__(self):
        self.name = "mock"
        # 每只股票的基准价格
        self._base_prices = {
            s[0]: random.uniform(5, 200) for s in _STOCK_LIST
        }

    def fetch_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        symbol = self.normalize_symbol(symbol)
        start = start_date or date(2023, 1, 1)
        end = end_date or date.today()

        base = self._base_prices.get(symbol, 50.0)
        rows = []
        d = start
        price = base

        while d <= end:
            if d.weekday() < 5:
                change = random.gauss(0, 0.02)
                o = round(price * (1 + random.uniform(-0.01, 0.01)), 2)
                c = round(price * (1 + change), 2)
                h = round(max(o, c) * (1 + abs(random.gauss(0, 0.01))), 2)
                l = round(min(o, c) * (1 - abs(random.gauss(0, 0.01))), 2)
                vol = random.randint(100000, 10000000)
                amt = round(vol * (o + c) / 2, 2)
                rows.append({
                    "symbol": symbol,
                    "trade_date": d,
                    "open": o, "high": h, "low": l, "close": c,
                    "volume": vol, "amount": amt,
                    "change_pct": round(change * 100, 2),
                    "turnover": round(random.uniform(0.3, 5.0), 2),
                })
                price = c
            d += timedelta(days=1)

        return pd.DataFrame(rows)

    def fetch_stock_list(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"symbol": s[0], "name": s[1], "exchange": s[2]}
            for s in _STOCK_LIST
        ])

    def get_realtime_quote(self, symbol: str) -> dict:
        symbol = self.normalize_symbol(symbol)
        base = self._base_prices.get(symbol, 50.0)
        change = random.uniform(-3, 3)
        price = round(base * (1 + change / 100), 2)
        return {
            "最新": price,
            "涨跌幅": round(change, 2),
            "最高": round(price * 1.02, 2),
            "最低": round(price * 0.98, 2),
            "成交量": random.randint(100000, 10000000),
            "成交额": round(random.uniform(1e8, 1e10), 2),
            "换手率": round(random.uniform(0.3, 5.0), 2),
        }
