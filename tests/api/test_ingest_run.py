import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from src.main import app
from src.db import get_session
import os
from unittest.mock import MagicMock
import importlib

# Shared setup for tests
engine = create_engine("sqlite://")

def override_get_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

def test_run_integration_success(monkeypatch, pathlib_tmpdir):
    # Setup Auth
    monkeypatch.setenv("CRM_API_KEY", "test-secret")
    
    # Mock integration folder
    integration_name = "test_crm"
    integration_dir = pathlib_tmpdir / integration_name
    integration_dir.mkdir()
    (integration_dir / "__init__.py").touch()
    
    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(pathlib_tmpdir))
    
    # Mock the module import
    mock_module = MagicMock()
    mock_module.fetch_contacts = lambda: [
        {
            "provider_id": "test_crm",
            "external_id": "ext-1",
            "full_name": "Test User",
            "primary_email": "test@example.com"
        }
    ]
    
    def mock_import(name):
        if name == f"src.integrations.{integration_name}":
            return mock_module
        raise ImportError()
        
    monkeypatch.setattr(importlib, "import_module", mock_import)

    response = client.get(
        f"/ingest/{integration_name}",
        headers={"X-API-Key": "test-secret"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["integration"] == integration_name
    assert data["fetched"] == 1
    assert data["created"] == 1

def test_run_integration_not_found(monkeypatch):
    monkeypatch.setenv("CRM_API_KEY", "test-secret")
    response = client.get(
        "/ingest/non_existent",
        headers={"X-API-Key": "test-secret"}
    )
    assert response.status_code == 404
    assert "Unknown integration" in response.json()["detail"]

def test_run_integration_failure_502(monkeypatch, pathlib_tmpdir):
    monkeypatch.setenv("CRM_API_KEY", "test-secret")
    
    integration_name = "failing_crm"
    integration_dir = pathlib_tmpdir / integration_name
    integration_dir.mkdir()
    (integration_dir / "__init__.py").touch()
    
    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(pathlib_tmpdir))
    
    mock_module = MagicMock()
    def fail(): raise Exception("API Down")
    mock_module.fetch_contacts = fail
    
    monkeypatch.setattr(importlib, "import_module", lambda n: mock_module)

    response = client.get(
        f"/ingest/{integration_name}",
        headers={"X-API-Key": "test-secret"}
    )
    
    assert response.status_code == 502
    assert "Integration failed: API Down" in response.json()["detail"]

@pytest.fixture
def pathlib_tmpdir(tmp_path):
    return tmp_path