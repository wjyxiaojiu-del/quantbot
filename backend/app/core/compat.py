"""
数据库兼容层：让 UUID 类型同时兼容 PostgreSQL 和 SQLite
"""
import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class UUID(TypeDecorator):
    """跨数据库 UUID 类型 — PG 用原生 UUID，SQLite 用 CHAR(32)"""
    impl = CHAR
    cache_ok = True

    def __init__(self):
        super().__init__(length=36)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.hex  # 存储为 32 位无短横线格式
        return uuid.UUID(value).hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        # 兼容有无短横线的 UUID 格式
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(value)
        except ValueError:
            # 无短横线格式：67c8c03eff524ce3b3e91e4425b22616
            return uuid.UUID(hex=value)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))
