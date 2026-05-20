from app.services.data.base import BaseDataSource
from app.core.config import get_settings


def get_data_source(name: str = None) -> BaseDataSource:
    """根据配置返回数据源实例
    name: 显式指定数据源，覆盖配置。用于多源聚合场景。
    """
    settings = get_settings()
    source = (name or settings.DATA_SOURCE).lower()

    if source == "eastmoney":
        from app.services.data.eastmoney_adapter import EastMoneyDataSource
        return EastMoneyDataSource()
    elif source == "yfinance":
        from app.services.data.yfinance_adapter import YFinanceDataSource
        return YFinanceDataSource()
    elif source == "mock":
        from app.services.data.mock_adapter import MockDataSource
        return MockDataSource()
    elif source == "akshare":
        from app.services.data.akshare_adapter import AKShareDataSource
        return AKShareDataSource()
    else:  # baostock (default)
        from app.services.data.baostock_adapter import BaostockDataSource
        return BaostockDataSource()


def get_data_source_for_symbol(symbol: str) -> BaseDataSource:
    """根据 symbol 自动选择最佳数据源
    - 含 .HK / .SS / 纯数字 → A股/港股 → akshare
    - 含 -USD / ^ 开头 → 美股/加密/指数 → yfinance
    - 其他美股代码 → yfinance
    """
    s = symbol.strip().upper()

    # A 股
    if s.endswith((".SZ", ".SH", ".BJ")) or s.endswith(".SS"):
        return get_data_source("akshare")
    if s.isdigit() and len(s) == 6:
        return get_data_source("akshare")

    # 港股
    if s.endswith(".HK"):
        return get_data_source("yfinance")

    # 加密货币 / 指数
    if "-USD" in s or s.startswith("^"):
        return get_data_source("yfinance")

    # 默认：美股等用 yfinance
    return get_data_source("yfinance")
