from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List, Dict, Any
import pandas as pd


class BaseDataSource(ABC):
    """数据源基类"""
    
    @abstractmethod
    def fetch_kline(
        self, 
        symbol: str, 
        period: str = "daily",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """获取 K 线数据
        
        Returns:
            DataFrame with columns: [trade_date, open, high, low, close, volume, amount, ...]
        """
        pass
    
    @abstractmethod
    def fetch_stock_list(self) -> pd.DataFrame:
        """获取股票列表

        Returns:
            DataFrame with columns: [symbol, name, exchange, industry, list_date]
        """
        pass

    def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情快照（子类可选实现）"""
        return {}

    def normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码"""
        symbol = symbol.strip().upper()
        if "." not in symbol:
            # 根据代码规则判断交易所
            if symbol.startswith("6"):
                symbol += ".SH"
            elif symbol.startswith(("0", "3")):
                symbol += ".SZ"
            elif symbol.startswith(("4", "8")):
                symbol += ".BJ"
        return symbol
