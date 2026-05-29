import pytest
from sqlmodel import Session, SQLModel, create_engine
from src.models.db import Contact
from src.repositories.contact_repo import ContactRepository

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_create_and_get_contact(session: Session):
    repo = ContactRepository(session)
    contact = Contact(
        full_name="John Doe",
        primary_email="JOHN@example.com",
        custom_fields={"internal_score": 10}
    )
    
    created = repo.create(contact)
    assert created.id is not None
    
    fetched = repo.get_by_email("john@example.com")
    assert fetched is not None
    assert fetched.full_name == "John Doe"
    assert fetched.custom_fields["internal_score"] == 10