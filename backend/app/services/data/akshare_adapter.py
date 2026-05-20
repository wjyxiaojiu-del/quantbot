import akshare as ak
import pandas as pd
from datetime import date, datetime
from typing import Optional
import logging

from app.services.data.base import BaseDataSource

logger = logging.getLogger(__name__)


class AKShareDataSource(BaseDataSource):
    """AKShare 数据源适配器"""
    
    def __init__(self):
        self.name = "akshare"
    
    def _format_date(self, d) -> Optional[str]:
        if d is None:
            return None
        if isinstance(d, str):
            # 支持 "2023-01-01" 或 "20230101" 格式
            d = d.replace("-", "")
            return d[:8]
        if isinstance(d, (date, datetime)):
            return d.strftime("%Y%m%d")
        return str(d)
    
    def _parse_symbol(self, symbol: str) -> tuple:
        """解析代码和交易所"""
        symbol = self.normalize_symbol(symbol)
        code, exchange = symbol.split(".")
        return code, exchange
    
    def fetch_kline(
        self, 
        symbol: str, 
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """获取 A 股历史 K 线"""
        code, exchange = self._parse_symbol(symbol)
        
        # AKShare 的 period 映射
        ak_period = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}.get(period, "daily")
        
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period=ak_period,
                start_date=self._format_date(start_date) or "19700101",
                end_date=self._format_date(end_date) or datetime.now().strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )
        except Exception as e:
            logger.error(f"AKShare fetch_kline failed for {symbol}: {e}")
            raise
        
        if df.empty:
            return df
        
        # 标准化列名
        df = df.rename(columns={
            "日期": "trade_date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
            "涨跌幅": "change_pct",
            "换手率": "turnover",
        })
        
        # 添加 symbol
        df["symbol"] = symbol
        
        # 确保日期格式正确
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        
        # 选择需要的列
        columns = ["symbol", "trade_date", "open", "high", "low", "close", 
                   "volume", "amount", "change_pct", "turnover"]
        df = df[[c for c in columns if c in df.columns]]
        
        return df
    
    def fetch_stock_list(self) -> pd.DataFrame:
        """获取 A 股所有股票列表"""
        try:
            # 上海
            df_sh = ak.stock_sh_a_spot_em()
            df_sh = df_sh[["代码", "名称"]]
            df_sh["exchange"] = "SH"
            
            # 深圳
            df_sz = ak.stock_sz_a_spot_em()
            df_sz = df_sz[["代码", "名称"]]
            df_sz["exchange"] = "SZ"
            
            # 北京
            df_bj = ak.stock_bj_a_spot_em()
            df_bj = df_bj[["代码", "名称"]]
            df_bj["exchange"] = "BJ"
            
            df = pd.concat([df_sh, df_sz, df_bj], ignore_index=True)
            
            df = df.rename(columns={
                "代码": "symbol_raw",
                "名称": "name",
            })
            
            # 生成带后缀的 symbol
            df["symbol"] = df.apply(
                lambda x: f"{x['symbol_raw']}.{x['exchange']}", axis=1
            )
            
            return df[["symbol", "name", "exchange"]]
            
        except Exception as e:
            logger.error(f"AKShare fetch_stock_list failed: {e}")
            raise
    
    def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情快照"""
        code, exchange = self._parse_symbol(symbol)
        
        try:
            # 使用 AKShare 获取实时行情
            df = ak.stock_bid_ask_em(symbol=code)
            if df.empty:
                return {}
            return df.to_dict("records")[0]
        except Exception as e:
            logger.error(f"AKShare realtime quote failed for {symbol}: {e}")
            return {}
