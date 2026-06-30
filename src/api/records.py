from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session
from src.db import get_session

from src.models.db import Record
from src.repositories.record_repo import RecordRepository
from src.models.schemas import RecordListResponse, StoredRecord

router = APIRouter(tags=["records"])


@router.get("", response_model=RecordListResponse)
def get_records(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    data_type: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """
    Get a paginated list of stored records.

    Returns every stored record regardless of data_type. Pass `data_type` to
    filter to a single type (e.g. "contact").
    """
    repo = RecordRepository(session)
    items, total = repo.list_records(
        data_type=data_type, limit=limit, offset=offset
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{record_id}", response_model=StoredRecord)
def get_record(
    record_id: int,
    session: Session = Depends(get_session),
):
    """
    Get a single stored record by ID.
    """
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record
