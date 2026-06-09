import pytest
from sqlmodel import Session, SQLModel, create_engine
from src.models.schemas import IncomingContact
from src.services.ingest import persist_incoming_contact
from src.models.db import Contact, SourceLink

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_persist_new_contact(session: Session):
    ic = IncomingContact(
        provider_id="pipedrive",
        external_id="pd-1",
        full_name="Alice",
        primary_email="alice@example.com"
    )
    
    contact, created = persist_incoming_contact(session, ic)
    assert created is True
    assert contact.id is not None
    assert contact.full_name == "Alice"
    
    # Check SourceLink
    links = session.query(SourceLink).filter_by(contact_id=contact.id).all()
    assert len(links) == 1
    assert links[0].provider_id == "pipedrive"
    assert links[0].external_id == "pd-1"

def test_persist_merge_existing(session: Session):
    # 1. Create existing
    existing = Contact(full_name="Bob", primary_email="bob@example.com")
    session.add(existing)
    session.commit()
    
    # 2. Ingest matching record with new data
    ic = IncomingContact(
        provider_id="salesforce",
        external_id="sf-1",
        full_name="Bob", # Matches via email
        primary_email="BOB@example.com",
        phone="555-1234"
    )
    
    merged, created = persist_incoming_contact(session, ic)
    assert created is False
    assert merged.id == existing.id
    assert merged.phone == "555-1234"
    
    # Verify two source links would exist if we added another, 
    # but here we check if the SF link was created.
    sf_link = session.query(SourceLink).filter_by(external_id="sf-1").first()
    assert sf_link.contact_id == existing.id