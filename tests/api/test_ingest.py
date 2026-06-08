import pytest
from fastapi.testclient import TestClient
from src.main import app
import os

client = TestClient(app)

def test_ingest_discovery_endpoint(monkeypatch):
    # Mock the service instead of the filesystem for API level test
    import src.api.ingest
    monkeypatch.setattr("src.api.ingest.discover_integrations", lambda: ["mock_crm"])

    response = client.post("/ingest/discover")

    assert response.status_code == 200
    assert response.json() == {"discovered": ["mock_crm"]}