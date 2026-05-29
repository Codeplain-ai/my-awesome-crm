from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr

class SourceLinkRead(BaseModel):
    provider_id: str
    external_id: str
    last_synced_at: datetime

class ContactRead(BaseModel):
    id: int
    full_name: str
    primary_email: EmailStr | None = None
    phone: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    source_links: list[SourceLinkRead]
    custom_fields: dict[str, Any]
    created_at: datetime
    updated_at: datetime

class ContactListResponse(BaseModel):
    items: list[ContactRead]
    total: int
    limit: int
    offset: int

class IncomingContact(BaseModel):
    provider_id: str
    external_id: str
    full_name: str
    primary_email: EmailStr | None = None
    phone: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    custom_fields: dict[str, Any] = {}