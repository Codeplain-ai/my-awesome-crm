from typing import Sequence
from sqlmodel import Session, select
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

    def list_all(self, limit: int = 100) -> Sequence[Contact]:
        statement = select(Contact).limit(limit)
        return self.session.exec(statement).all()