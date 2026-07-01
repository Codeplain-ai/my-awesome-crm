import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool
from src.main import app
from src.db import get_session
from src.models.db import Record


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


def test_get_records_empty(client: TestClient):
    response = client.get("/records")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_get_records_pagination_and_type_filter(client: TestClient, session: Session):
    # Seed rows across two data_types and two sources.
    session.add(Record(data_type="contact", source="salesforce", data={"full_name": "Alice"}))
    session.add(Record(data_type="contact", source="pipedrive", data={"full_name": "Bob"}))
    session.add(Record(data_type="account", source="salesforce", data={"name": "Acme"}))
    session.commit()

    # Every stored record, regardless of data_type.
    response = client.get("/records")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Filtered to a single data_type.
    response = client.get("/records?data_type=contact")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["data_type"] == "contact" for item in data["items"])
    assert all(item["source"] in {"salesforce", "pipedrive"} for item in data["items"])

    # Pagination is independent of the filter.
    response = client.get("/records?limit=1&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["limit"] == 1
    assert data["offset"] == 1


def test_get_records_limit_validation(client: TestClient):
    # limit must be within 1..200.
    assert client.get("/records?limit=201").status_code == 422
    assert client.get("/records?limit=0").status_code == 422


def test_get_record_by_id(client: TestClient, session: Session):
    record = Record(data_type="contact", source="salesforce", data={"full_name": "Single Test"})
    session.add(record)
    session.commit()
    session.refresh(record)

    # Success case
    response = client.get(f"/records/{record.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == record.id
    assert body["data_type"] == "contact"
    assert body["source"] == "salesforce"
    assert body["data"]["full_name"] == "Single Test"

    # Not found case
    response = client.get("/records/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"
