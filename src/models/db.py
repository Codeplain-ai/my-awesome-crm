from datetime import datetime
from typing import Any
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Record(SQLModel, table=True):
    """A generic stored row.

    The store is deliberately untyped: every row carries a ``data_type``
    (e.g. ``"contact"``) and a free-form JSON ``data`` payload. ``source`` names
    the integration that produced the row. A re-sync upserts on
    ``(source, data_type, external_id)``: matching rows are updated in place, new
    rows are inserted, and nothing is deleted. Rows are stored verbatim.
    """

    id: int | None = Field(default=None, primary_key=True)
    data_type: str = Field(index=True)
    source: str = Field(index=True)
    data: dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
