from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    code: str
    params: Optional[Dict[str, Any]] = {}


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    code: str
    params: Dict[str, Any] = {}
    status: str = "draft"
    version: int = 1
    is_public: bool = False
    created_at: datetime
    updated_at: datetime


class StrategyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    status: str = "draft"
    version: int = 1
    created_at: datetime
    updated_at: datetime
