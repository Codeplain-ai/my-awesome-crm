import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine
from src.models.db import Contact, SourceLink
from src.repositories.source_link_repo import SourceLinkRepository

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://")
    # Enable FKs for testing
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_unique_constraint_provider_external(session: Session):
    repo = SourceLinkRepository(session)
    
    link1 = SourceLink(provider_id="hubspot", external_id="123")
    repo.create(link1)
    
    link2 = SourceLink(provider_id="hubspot", external_id="123")
    session.add(link2)
    with pytest.raises(IntegrityError):
        session.commit()

def test_foreign_key_constraint(session: Session):
    # Try to create a link pointing to non-existent contact
    link = SourceLink(provider_id="salesforce", external_id="sf-1", contact_id=999)
    session.add(link)
    with pytest.raises(IntegrityError) as excinfo:
        session.commit()
    assert "FOREIGN KEY constraint failed" in str(excinfo.value)