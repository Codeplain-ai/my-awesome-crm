import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool
from src.main import app
from src.db import get_session
from src.models.db import SQLModel # Use the metadata from the models package
import os
from unittest.mock import MagicMock
import importlib

@pytest.fixture(name="engine")
def engine_fixture():
    # Create a fresh in-memory database for every test
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from src.models import db # Force import to register tables
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session

@pytest.fixture(autouse=True)
def override_session(engine):
    def get_session_override():
        with Session(engine) as session:
            yield session
    
    app.dependency_overrides[get_session] = get_session_override
    yield
    app.dependency_overrides.clear()

@pytest.fixture(name="client")
def client_fixture():
    return TestClient(app)

def test_run_integration_success(client, monkeypatch, pathlib_tmpdir):
    # Mock integration folder
    integration_name = "test_crm"
    integration_dir = pathlib_tmpdir / integration_name
    integration_dir.mkdir()
    (integration_dir / "__init__.py").touch()
    
    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(pathlib_tmpdir))
    
    # Mock the module import — the current host contract is fetch(get_stored),
    # returning a list of {data_type, data} dicts (not the old fetch_contacts()).
    mock_module = MagicMock()
    mock_module.DATA_TYPE = "contact"
    mock_module.fetch = lambda get_stored: [
        {
            "data_type": "contact",
            "data": {
                "provider_id": "test_crm",
                "external_id": "ext-1",
                "full_name": "Test User",
                "primary_email": "test@example.com",
            },
        }
    ]

    def mock_import(name):
        if name == f"src.integrations.{integration_name}":
            return mock_module
        raise ImportError()

    monkeypatch.setattr(importlib, "import_module", mock_import)

    response = client.get(f"/ingest/{integration_name}")

    assert response.status_code == 200
    data = response.json()
    assert data["integration"] == integration_name
    assert data["fetched"] == 1
    assert data["stored"] == 1
    assert data["replaced"] == 0
    assert data["data_types"] == {"contact": 1}

def _mock_integration(monkeypatch, pathlib_tmpdir, integration_name, records):
    """Wire up a fake integration whose fetch() returns `records` (a list or a
    zero-arg callable returning a fresh list each call)."""
    integration_dir = pathlib_tmpdir / integration_name
    if not integration_dir.exists():
        integration_dir.mkdir()
        (integration_dir / "__init__.py").touch()
    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(pathlib_tmpdir))

    mock_module = MagicMock()
    mock_module.DATA_TYPE = "contact"
    mock_module.fetch = lambda get_stored: (records() if callable(records) else records)

    def mock_import(name):
        if name == f"src.integrations.{integration_name}":
            return mock_module
        raise ImportError()

    monkeypatch.setattr(importlib, "import_module", mock_import)


def _contact(ext_id, name="Test User", email="test@example.com"):
    return {
        "data_type": "contact",
        "data": {
            "provider_id": "test_crm",
            "external_id": ext_id,
            "full_name": name,
            "primary_email": email,
        },
    }


def test_resync_identical_data_is_idempotent(client, monkeypatch, pathlib_tmpdir):
    # Same 2 records returned on every sync.
    _mock_integration(monkeypatch, pathlib_tmpdir, "test_crm",
                      [_contact("ext-1"), _contact("ext-2")])

    first = client.get("/ingest/test_crm").json()
    assert (first["fetched"], first["stored"], first["replaced"]) == (2, 2, 0)

    second = client.get("/ingest/test_crm").json()
    # Nothing new, nothing changed — nothing deleted.
    assert second["fetched"] == 2
    assert second["stored"] == 0
    assert second["replaced"] == 0
    assert second["unchanged"] == 2

    # The store did not grow or shrink across the re-sync.
    assert client.get("/records").json()["total"] == 2


def test_resync_updates_changed_record_in_place(client, monkeypatch, pathlib_tmpdir):
    state = {"records": [_contact("ext-1", name="Old Name")]}
    _mock_integration(monkeypatch, pathlib_tmpdir, "test_crm", lambda: state["records"])

    client.get("/ingest/test_crm")

    # Same external_id, changed name → update in place, not a new row.
    state["records"] = [_contact("ext-1", name="New Name")]
    result = client.get("/ingest/test_crm").json()
    assert result["stored"] == 0
    assert result["replaced"] == 1
    assert result["unchanged"] == 0

    records = client.get("/records").json()
    assert records["total"] == 1
    assert records["items"][0]["data"]["full_name"] == "New Name"


def test_resync_inserts_new_records_without_touching_existing(client, monkeypatch, pathlib_tmpdir):
    state = {"records": [_contact("ext-1")]}
    _mock_integration(monkeypatch, pathlib_tmpdir, "test_crm", lambda: state["records"])

    client.get("/ingest/test_crm")

    # ext-1 unchanged, ext-2 is new.
    state["records"] = [_contact("ext-1"), _contact("ext-2")]
    result = client.get("/ingest/test_crm").json()
    assert result["stored"] == 1
    assert result["replaced"] == 0
    assert result["unchanged"] == 1
    assert client.get("/records").json()["total"] == 2


def test_run_integration_not_found(client, monkeypatch):
    response = client.get("/ingest/non_existent")
    assert response.status_code == 404
    assert "Unknown integration" in response.json()["detail"]

def test_run_integration_failure_502(client, monkeypatch, pathlib_tmpdir):
    integration_name = "failing_crm"
    integration_dir = pathlib_tmpdir / integration_name
    integration_dir.mkdir()
    (integration_dir / "__init__.py").touch()
    
    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(pathlib_tmpdir))
    
    mock_module = MagicMock()
    def fail(get_stored): raise Exception("API Down")
    mock_module.fetch = fail

    monkeypatch.setattr(importlib, "import_module", lambda n: mock_module)

    response = client.get(f"/ingest/{integration_name}")

    assert response.status_code == 502
    assert "Integration failed: API Down" in response.json()["detail"]

@pytest.fixture
def pathlib_tmpdir(tmp_path):
    return tmp_path