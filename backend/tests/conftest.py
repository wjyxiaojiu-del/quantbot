import pytest
import os
import uuid
from unittest.mock import patch


@pytest.fixture(autouse=True, scope="session")
def setup_test_env(tmp_path_factory):
    """整个测试会话使用 SQLite 临时数据库"""
    tmp_dir = tmp_path_factory.mktemp("data")
    db_path = tmp_dir / "test.db"
    test_db_url = f"sqlite:///{db_path}"

    with patch.dict(os.environ, {
        "DATABASE_URL": test_db_url,
        "DATA_SOURCE": "mock",
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "DEBUG": "true",
    }):
        from app.core.config import get_settings
        get_settings.cache_clear()

        from app.core import database
        from sqlalchemy import create_engine
        database.engine = create_engine(test_db_url, pool_pre_ping=True)
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

        from app.models import user, strategy, trade, backtest, kline
        database.Base.metadata.create_all(bind=database.engine)

        # 让 get_data_source_for_symbol 在测试中使用 mock
        from app.services.data import mock_adapter
        _mock_ds = mock_adapter.MockDataSource()

        import app.services.data as _ds_module
        _original_get_ds_for_symbol = _ds_module.get_data_source_for_symbol
        _ds_module.get_data_source_for_symbol = lambda symbol: _mock_ds

        yield

        _ds_module.get_data_source_for_symbol = _original_get_ds_for_symbol
        get_settings.cache_clear()


from sqlalchemy.orm import sessionmaker
