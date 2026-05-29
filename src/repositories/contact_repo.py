from typing import Sequence
from sqlmodel import Session, select, or_, func, desc
from src.models.db import Contact

class ContactRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, contact: Contact) -> Contact:
        if contact.primary_email:
            contact.primary_email = contact.primary_email.strip().lower()
        self.session.add(contact)
        self.session.commit()
        self.session.refresh(contact)
        return contact

    def get_by_id(self, contact_id: int) -> Contact | None:
        return self.session.get(Contact, contact_id)

    def get_by_email(self, email: str) -> Contact | None:
        # Search by lowercased email for deduping
        statement = select(Contact).where(Contact.primary_email == email.lower())
        return self.session.exec(statement).first()

    def list_contacts(
        self, 
        limit: int = 50, 
        offset: int = 0, 
        q: str | None = None
    ) -> tuple[Sequence[Contact], int]:
        query = select(Contact)
        
        if q:
            # Case-insensitive substring search on full_name and primary_email
            query = query.where(
                or_(
                    Contact.full_name.contains(q),
                    Contact.primary_email.contains(q)
                )
            )

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.exec(count_query).one()

        # Apply sorting: updated_at DESC, id ASC
        query = query.order_by(desc(Contact.updated_at), Contact.id)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        return self.session.exec(query).all(), total