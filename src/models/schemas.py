from datetime import datetime
from typing import Any
from pydantic import BaseModel


class StoredRecord(BaseModel):
    """API view of one stored row."""
    id: int
    data_type: str
    source: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RecordListResponse(BaseModel):
    items: list[StoredRecord]
    total: int
    limit: int
    offset: int
