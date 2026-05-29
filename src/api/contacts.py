from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session
from src.db import get_session

from src.repositories.contact_repo import ContactRepository
from src.models.schemas import ContactListResponse, ContactRead

router = APIRouter(tags=["contacts"])

@router.get("", response_model=ContactListResponse)
def get_contacts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """
    Get a paginated list of consolidated contacts.
    """
    repo = ContactRepository(session)
    items, total = repo.list_contacts(limit=limit, offset=offset, q=q)
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(
    contact_id: int,
    session: Session = Depends(get_session),
):
    """
    Get a single consolidated contact by ID.
    """
    repo = ContactRepository(session)
    contact = repo.get_by_id(contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=404, 
            detail=f"Contact not found"
        )
    
    return contact