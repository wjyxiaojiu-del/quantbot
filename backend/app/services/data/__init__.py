from app.services.data.base import BaseDataSource
from app.core.config import get_settings


def get_data_source() -> BaseDataSource:
    """根据配置返回数据源实例"""
    settings = get_settings()
    source = settings.DATA_SOURCE.lower()

    if source == "eastmoney":
        from app.services.data.eastmoney_adapter import EastMoneyDataSource
        return EastMoneyDataSource()
    elif source == "akshare":
        from app.services.data.akshare_adapter import AKShareDataSource
        return AKShareDataSource()
    elif source == "mock":
        from app.services.data.mock_adapter import MockDataSource
        return MockDataSource()
    else:  # baostock (default)
        from app.services.data.baostock_adapter import BaostockDataSource
        return BaostockDataSource()
