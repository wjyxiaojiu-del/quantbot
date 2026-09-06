"""
Baostock 数据源适配器
- 免费、无需注册、无代理问题
- 支持 A 股日/周/月 K 线、股票列表
- 实时行情走东方财富备用
"""

import baostock as bs
import pandas as pd
from datetime import date
from typing import Optional
import logging
import atexit

from app.services.data.base import BaseDataSource

logger = logging.getLogger(__name__)

# baostock 全局登录（只需一次）
_logged_in = False


def _ensure_login():
    global _logged_in
    if not _logged_in:
        lg = bs.login()
        if lg.error_code != "0":
            logger.error(f"baostock login failed: {lg.error_msg}")
        _logged_in = True
        atexit.register(lambda: bs.logout())


def _to_bs_code(symbol: str) -> str:
    """000001.SZ → sz.000001"""
    code, exchange = symbol.split(".")
    return f"{exchange.lower()}.{code}"


def _from_bs_code(bs_code: str) -> str:
    """sz.000001 → 000001.SZ"""
    parts = bs_code.split(".")
    return f"{parts[1]}.{parts[0].upper()}"


class BaostockDataSource(BaseDataSource):
    """Baostock 数据源"""

    def __init__(self):
        self.name = "baostock"
        _ensure_login()

    def fetch_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        symbol = self.normalize_symbol(symbol)
        bs_code = _to_bs_code(symbol)

        freq_map = {
            "daily": "d", "weekly": "w", "monthly": "m",
            "5m": "5", "15m": "15", "30m": "30", "60m": "60",
        }
        freq = freq_map.get(period, "d")

        start = start_date.strftime("%Y-%m-%d") if start_date else "2010-01-01"
        end = end_date.strftime("%Y-%m-%d") if end_date else date.today().strftime("%Y-%m-%d")

        # 分钟线需要 time 字段
        if freq in ("5", "15", "30", "60"):
            fields = "date,time,open,high,low,close,volume,amount"
        else:
            fields = "date,open,high,low,close,volume,amount,turn,pctChg"

        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                fields,
                start_date=start,
                end_date=end,
                frequency=freq,
                adjustflag="2",  # 前复权
            )
        except Exception as e:
            logger.error(f"baostock fetch_kline failed for {symbol}: {e}")
            raise

        if rs.error_code != "0":
            logger.error(f"baostock query error: {rs.error_msg}")
            return pd.DataFrame()

        data = []
        while rs.error_code == "0" and rs.next():
            data.append(rs.get_row_data())

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=rs.fields)

        # 类型转换
        df["symbol"] = symbol

        # 分钟线有 time 字段，日线只有 date
        is_minute = "time" in df.columns
        if is_minute:
            # 分钟线：20250520093500000 -> datetime
            df["trade_date"] = pd.to_datetime(df["time"].str[:14], format="%Y%m%d%H%M%S")
        else:
            df["trade_date"] = pd.to_datetime(df["date"]).dt.date

        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = (df["volume"].astype(float) / 100).astype(int)  # 股→手
        df["amount"] = df["amount"].astype(float)

        # 分钟线没有换手率和涨跌幅
        if not is_minute:
            df["change_pct"] = pd.to_numeric(df["pctChg"], errors="coerce")
            df["turnover"] = pd.to_numeric(df["turn"], errors="coerce")
        else:
            df["change_pct"] = None
            df["turnover"] = None

        columns = ["symbol", "trade_date", "open", "high", "low", "close",
                    "volume", "amount", "change_pct", "turnover"]
        return df[[c for c in columns if c in df.columns]]

    def fetch_stock_list(self) -> pd.DataFrame:
        try:
            rs = bs.query_stock_basic()
        except Exception as e:
            logger.error(f"baostock fetch_stock_list failed: {e}")
            return pd.DataFrame()

        if rs.error_code != "0":
            return pd.DataFrame()

        data = []
        while rs.error_code == "0" and rs.next():
            data.append(rs.get_row_data())

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=rs.fields)
        # 只保留 A 股：type=1（股票），status=1（上市中）
        df = df[(df["type"] == "1") & (df["status"] == "1")]
        df["symbol"] = df["code"].apply(_from_bs_code)
        df["name"] = df["code_name"]
        df["exchange"] = df["symbol"].apply(lambda x: x.split(".")[1])

        return df[["symbol", "name", "exchange"]].reset_index(drop=True)

    def get_realtime_quote(self, symbol: str) -> dict:
        """实时行情 — baostock 不支持，用东方财富备用"""
        try:
            import urllib.request, json
            code, exchange = self.normalize_symbol(symbol).split(".")
            secid = f"{'0' if exchange == 'SZ' else '1'}.{code}"
            url = (
                f"https://push2.eastmoney.com/api/qt/stock/get?"
                f"secid={secid}&ut=fa5fd1943c7b386f172d6893dbbd1d0c"
                f"&fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f170&invt=2"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            resp = opener.open(req, timeout=8)
            data = json.loads(resp.read().decode("utf-8")).get("data", {})
            if not data:
                return {}
            return {
                "最新": data.get("f43", 0) / 100 if data.get("f43") else None,
                "涨跌幅": data.get("f170", 0) / 100 if data.get("f170") else None,
                "最高": data.get("f44", 0) / 100 if data.get("f44") else None,
                "最低": data.get("f45", 0) / 100 if data.get("f45") else None,
                "成交量": data.get("f47", 0),
                "成交额": data.get("f48", 0),
                "换手率": data.get("f50", 0) / 100 if data.get("f50") else None,
            }
        except Exception as e:
            logger.warning(f"实时行情获取失败 {symbol}: {e}")
            return {}
