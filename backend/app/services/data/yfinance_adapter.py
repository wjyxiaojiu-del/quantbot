"""
Yahoo Finance 数据源适配器
- 免费、全球覆盖（美股/港股/加密货币/ETF/指数）
- 无需 API key，无需注册
- 支持日/周/月 K 线
- 自动走代理（Clash 7890 / v2ray 10808）
"""

import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Optional
import logging
import re
import os

from app.services.data.base import BaseDataSource

logger = logging.getLogger(__name__)


def _to_yf_symbol(symbol: str) -> str:
    """将内部 symbol 转为 yfinance 格式
    - AAPL / TSLA → 原样返回（美股）
    - 000001.SZ → 000001.SZ（A股，yfinance 直接支持）
    - 0700.HK → 0700.HK（港股）
    - BTC-USD → BTC-USD（加密货币）
    """
    symbol = symbol.strip().upper()

    # 已经是 yfinance 格式（含 . 或 -）
    if "." in symbol or "-" in symbol:
        return symbol

    # 纯数字 → A 股，需要补交易所后缀
    if re.match(r"^\d{6}$", symbol):
        if symbol.startswith("6"):
            return f"{symbol}.SS"
        elif symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"
        elif symbol.startswith(("4", "8")):
            return f"{symbol}.BJ"

    # 其他（如 AAPL, TSLA, BTC-USD）原样返回
    return symbol


def _from_yf_symbol(yf_symbol: str) -> str:
    """yfinance 格式转内部 symbol
    - 000001.SS → 000001.SH
    - 000001.SZ → 000001.SZ（不变）
    - AAPL → AAPL（不变）
    """
    if yf_symbol.endswith(".SS"):
        return yf_symbol.replace(".SS", ".SH")
    return yf_symbol


def _setup_proxy():
    """设置代理（Clash 7890 / v2ray 10808）"""
    # 如果已有代理配置，不覆盖
    if os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"):
        return

    # 尝试 Clash
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", 7890))
        sock.close()
        if result == 0:
            os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
            os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
            logger.info("yfinance: using Clash proxy at 127.0.0.1:7890")
            return
    except Exception:
        pass

    # 尝试 v2ray
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", 10808))
        sock.close()
        if result == 0:
            os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
            os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"
            logger.info("yfinance: using v2ray proxy at 127.0.0.1:10808")
            return
    except Exception:
        pass

    logger.warning("yfinance: no proxy detected, may fail due to GFW")


class YFinanceDataSource(BaseDataSource):
    """Yahoo Finance 数据源适配器"""

    def __init__(self):
        self.name = "yfinance"
        _setup_proxy()

    def fetch_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        import yfinance as yf

        yf_symbol = _to_yf_symbol(symbol)

        # yfinance period 映射
        yf_interval = {
            "daily": "1d",
            "weekly": "1wk",
            "monthly": "1mo",
        }.get(period, "1d")

        start = start_date or date(2010, 1, 1)
        end = end_date or date.today()

        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval=yf_interval,
                auto_adjust=True,
            )
        except Exception as e:
            logger.error(f"yfinance fetch_kline failed for {yf_symbol}: {e}")
            raise

        if df.empty:
            return pd.DataFrame()

        # 标准化
        internal_symbol = _from_yf_symbol(yf_symbol)
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "trade_date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })

        df["symbol"] = internal_symbol
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        df["amount"] = df["close"] * df["volume"]
        df["change_pct"] = df["close"].pct_change() * 100
        df["turnover"] = 0.0  # yfinance 无换手率

        columns = ["symbol", "trade_date", "open", "high", "low", "close",
                    "volume", "amount", "change_pct", "turnover"]
        return df[[c for c in columns if c in df.columns]].reset_index(drop=True)

    def fetch_stock_list(self) -> pd.DataFrame:
        """yfinance 没有统一股票列表接口，返回常用标的"""
        watchlist = [
            # 美股大盘
            ("AAPL", "苹果", "US"), ("MSFT", "微软", "US"),
            ("GOOGL", "谷歌", "US"), ("AMZN", "亚马逊", "US"),
            ("TSLA", "特斯拉", "US"), ("NVDA", "英伟达", "US"),
            ("META", "Meta", "US"), ("NFLX", "奈飞", "US"),
            ("AMD", "AMD", "US"), ("INTC", "英特尔", "US"),
            # 中概股
            ("BABA", "阿里巴巴", "US"), ("JD", "京东", "US"),
            ("PDD", "拼多多", "US"), ("BIDU", "百度", "US"),
            ("NIO", "蔚来", "US"), ("XPEV", "小鹏", "US"),
            ("LI", "理想", "US"),
            # 港股
            ("0700.HK", "腾讯控股", "HK"), ("9988.HK", "阿里巴巴-W", "HK"),
            ("9618.HK", "京东集团-SW", "HK"), ("1810.HK", "小米集团-W", "HK"),
            ("2318.HK", "中国平安", "HK"), ("0941.HK", "中国移动", "HK"),
            # 加密货币
            ("BTC-USD", "比特币", "CRYPTO"), ("ETH-USD", "以太坊", "CRYPTO"),
            ("SOL-USD", "Solana", "CRYPTO"), ("DOGE-USD", "狗狗币", "CRYPTO"),
            # 指数/ETF
            ("^GSPC", "标普500", "INDEX"), ("^IXIC", "纳斯达克", "INDEX"),
            ("^DJI", "道琼斯", "INDEX"), ("000300.SS", "沪深300", "INDEX"),
            ("SPY", "SPDR标普500ETF", "ETF"), ("QQQ", "纳斯达克100ETF", "ETF"),
        ]

        return pd.DataFrame([
            {"symbol": s[0], "name": s[1], "exchange": s[2]}
            for s in watchlist
        ])

    def get_realtime_quote(self, symbol: str) -> dict:
        import yfinance as yf

        yf_symbol = _to_yf_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.fast_info
            return {
                "最新": float(info.get("lastPrice", info.get("last_price", 0)) or 0),
                "涨跌幅": round(float(info.get("lastPrice", 0) or 0) / float(info.get("previousClose", 1) or 1) * 100 - 100, 2) if info.get("previousClose") else 0,
                "最高": float(info.get("dayHigh", 0) or 0),
                "最低": float(info.get("dayLow", 0) or 0),
                "成交量": int(info.get("lastVolume", 0) or 0),
                "市值": float(info.get("marketCap", 0) or 0),
            }
        except Exception as e:
            logger.warning(f"yfinance realtime quote failed for {yf_symbol}: {e}")
            return {}
