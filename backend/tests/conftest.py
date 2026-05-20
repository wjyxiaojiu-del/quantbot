import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    """每个测试用例自动使用 SQLite 临时数据库"""
    db_path = tmp_path / "test.db"
    test_db_url = f"sqlite:///{db_path}"

    with patch.dict(os.environ, {
        "DATABASE_URL": test_db_url,
        "DATA_SOURCE": "mock",
        "SECRET_KEY": "test-secret-key-for-testing-only",
    }):
        # 清除 lru_cache，让 Settings 重新读取环境变量
        from app.core.config import get_settings
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
