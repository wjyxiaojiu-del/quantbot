"""
东方财富数据直连适配器
直接调用东方财富公开 HTTP API，不依赖 AKShare
"""

import httpx
import pandas as pd
from datetime import date, datetime
from typing import Optional
import logging

from app.services.data.base import BaseDataSource

logger = logging.getLogger(__name__)

# 东方财富 API 常量
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
SPOT_URL = "https://82.push2.eastmoney.com/api/qt/clist/get"
REALTIME_URL = "https://push2.eastmoney.com/api/qt/stock/get"

# secid 映射：SZ→0, SH→1, BJ→0
_EXCHANGE_MAP = {"SZ": "0", "SH": "1", "BJ": "0"}


def _secid(symbol: str) -> str:
    """000001.SZ → 0.000001"""
    code, exchange = symbol.split(".")
    return f"{_EXCHANGE_MAP.get(exchange, '0')}.{code}"


class EastMoneyDataSource(BaseDataSource):
    """东方财富 HTTP 直连数据源"""

    def __init__(self, timeout: int = 15):
        self.name = "eastmoney"
        self.timeout = timeout
        # 强制绕过系统代理（Windows 系统代理会导致东方财富连接失败）
        import os
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)
        os.environ.pop("ALL_PROXY", None)
        os.environ["NO_PROXY"] = "*"

        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
            proxy=None,
            trust_env=False,
        )

    def _parse_symbol(self, symbol: str) -> tuple:
        symbol = self.normalize_symbol(symbol)
        code, exchange = symbol.split(".")
        return code, exchange

    # ── K 线 ──

    def fetch_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        code, exchange = self._parse_symbol(symbol)
        secid = _secid(f"{code}.{exchange}")

        # klt: 101=日K, 102=周K, 103=月K
        klt_map = {"daily": "101", "weekly": "102", "monthly": "103"}
        klt = klt_map.get(period, "101")

        beg = start_date.strftime("%Y%m%d") if start_date else "19700101"
        end = end_date.strftime("%Y%m%d") if end_date else "20500101"

        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": "1",  # 前复权
            "beg": beg,
            "end": end,
            "lmt": "5000",
            "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
        }

        try:
            resp = self._client.get(KLINE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"东方财富 K 线请求失败 {symbol}: {e}")
            raise

        klines = data.get("data", {}).get("klines")
        if not klines:
            return pd.DataFrame()

        # klines 格式: "2024-01-02,12.50,12.80,12.90,12.40,500000,6250000.00,3.20,1.50,0.05,0.40"
        rows = []
        for line in klines:
            parts = line.split(",")
            if len(parts) < 7:
                continue
            rows.append({
                "symbol": f"{code}.{exchange}",
                "trade_date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": int(float(parts[5])),
                "amount": float(parts[6]),
                "change_pct": float(parts[8]) if len(parts) > 8 and parts[8] else None,
                "turnover": float(parts[10]) if len(parts) > 10 and parts[10] else None,
            })

        df = pd.DataFrame(rows)
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        return df

    # ── 股票列表 ──

    def fetch_stock_list(self) -> pd.DataFrame:
        frames = []
        for fs, exchange in [
            ("m:1+t:2,m:1+t:23", "SH"),   # 沪A主板+科创板
            ("m:0+t:6,m:0+t:80", "SZ"),    # 深A主板+创业板
            ("m:0+t:81+s:2048", "BJ"),      # 北交所
        ]:
            try:
                df = self._fetch_spot(fs, exchange)
                if not df.empty:
                    frames.append(df)
            except Exception as e:
                logger.warning(f"获取 {exchange} 股票列表失败: {e}")

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def _fetch_spot(self, fs: str, exchange: str) -> pd.DataFrame:
        """获取某个交易所的股票列表快照"""
        params = {
            "pn": "1",
            "pz": "10000",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": fs,
            "fields": "f12,f14",  # f12=代码, f14=名称
        }

        resp = self._client.get(SPOT_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("data", {}).get("diff", [])
        if not items:
            return pd.DataFrame()

        rows = []
        for item in items:
            code = item.get("f12", "")
            name = item.get("f14", "")
            if code and name:
                rows.append({
                    "symbol": f"{code}.{exchange}",
                    "name": name,
                    "exchange": exchange,
                })

        return pd.DataFrame(rows)

    # ── 实时行情 ──

    def get_realtime_quote(self, symbol: str) -> dict:
        code, exchange = self._parse_symbol(symbol)
        secid = _secid(f"{code}.{exchange}")

        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
            "fields": "f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f170",
            "invt": "2",
        }

        try:
            resp = self._client.get(REALTIME_URL, params=params)
            resp.raise_for_status()
            data = resp.json().get("data", {})
        except Exception as e:
            logger.error(f"东方财富实时行情失败 {symbol}: {e}")
            return {}

        if not data:
            return {}

        # 字段映射
        return {
            "最新": data.get("f43", 0) / 100 if data.get("f43") else None,
            "涨跌幅": data.get("f170", 0) / 100 if data.get("f170") else None,
            "最高": data.get("f44", 0) / 100 if data.get("f44") else None,
            "最低": data.get("f45", 0) / 100 if data.get("f45") else None,
            "成交量": data.get("f47", 0),
            "成交额": data.get("f48", 0),
            "换手率": data.get("f50", 0) / 100 if data.get("f50") else None,
        }

    def close(self):
        self._client.close()
