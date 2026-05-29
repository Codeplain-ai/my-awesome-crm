import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool
from src.main import app
from src.db import get_session
from src.models.db import Contact
import os

@pytest.fixture(name="session")
def session_fixture():
    # Use StaticPool to share the same in-memory database across connections
    # and check_same_thread=False for FastAPI's multi-threaded nature.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_get_contacts_unauthorized(client: TestClient):
    response = client.get("/contacts")
    assert response.status_code == 401

def test_get_contacts_empty(client: TestClient, monkeypatch):
    monkeypatch.setenv("CRM_API_KEY", "test-secret")
    response = client.get("/contacts", headers={"X-API-Key": "test-secret"})
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0

def test_get_contacts_search_and_pagination(client: TestClient, session: Session, monkeypatch):
    monkeypatch.setenv("CRM_API_KEY", "test-secret")
    
    # Seed data
    c1 = Contact(full_name="Alice Smith", primary_email="alice@example.com")
    c2 = Contact(full_name="Bob Jones", primary_email="bob@provider.com")
    c3 = Contact(full_name="Charlie Smith", primary_email="charlie@other.com")
    session.add(c1)
    session.add(c2)
    session.add(c3)
    session.commit()

    # Test search 'Smith'
    response = client.get("/contacts?q=Smith", headers={"X-API-Key": "test-secret"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert any(i["full_name"] == "Alice Smith" for i in data["items"])
    assert any(i["full_name"] == "Charlie Smith" for i in data["items"])

    # Test pagination
    response = client.get("/contacts?limit=1&offset=1", headers={"X-API-Key": "test-secret"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["limit"] == 1
    assert data["offset"] == 1

def test_get_contacts_limit_validation(client: TestClient, monkeypatch):
    monkeypatch.setenv("CRM_API_KEY", "test-secret")
    # Limit 201 should trigger FastAPI validation error (422)
    response = client.get("/contacts?limit=201", headers={"X-API-Key": "test-secret"})
    assert response.status_code == 422