from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, JSON, func
from app.core.database import Base
from app.core.compat import UUID
import uuid


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True, comment="策略名称")
    description = Column(Text, nullable=True, comment="策略描述")
    code = Column(Text, nullable=False, comment="策略代码")
    params = Column(JSON, default=dict, comment="策略参数")
    status = Column(String(20), default="draft", comment="draft/active/archived")
    version = Column(Integer, default=1, comment="版本号")
    is_public = Column(Boolean, default=False, comment="是否公开")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
