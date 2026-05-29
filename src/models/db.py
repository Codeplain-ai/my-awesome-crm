from datetime import datetime
from typing import Any
from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel
from pydantic import field_validator

class SourceLink(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("provider_id", "external_id", name="uq_sourcelink_provider_external"),
    )
    id: int | None = Field(default=None, primary_key=True)
    provider_id: str = Field(index=True)
    external_id: str = Field(index=True)
    last_synced_at: datetime = Field(default_factory=datetime.utcnow)
    
    contact_id: int | None = Field(default=None, foreign_key="contact.id")
    contact: "Contact" = Relationship(back_populates="source_links")

class Contact(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(index=True)
    primary_email: str | None = Field(default=None, index=True)
    phone: str | None = Field(default=None)
    job_title: str | None = Field(default=None)
    company_name: str | None = Field(default=None)
    
    custom_fields: dict[str, Any] = Field(
        sa_column=Column(JSON), 
        default_factory=dict
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    source_links: list[SourceLink] = Relationship(back_populates="contact")

    @field_validator("primary_email", mode="before")
    @classmethod
    def lowercase_email(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().lower() or None
        return v