import pytest
import os
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
        # 清除 lru_cache，让 Settings 重新读取环境变量
        from app.core.config import get_settings
        get_settings.cache_clear()

        # 重新创建数据库引擎
        from app.core import database
        from sqlalchemy import create_engine
        database.engine = create_engine(test_db_url, pool_pre_ping=True)
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

        # 创建表
        from app.models import user, strategy, trade, backtest
        database.Base.metadata.create_all(bind=database.engine)

        yield

        get_settings.cache_clear()


from sqlalchemy.orm import sessionmaker
