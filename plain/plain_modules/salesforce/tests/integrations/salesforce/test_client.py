import pytest
from unittest.mock import MagicMock
from src.integrations.salesforce import client

def test_fetch_contacts_missing_credentials(monkeypatch):
    monkeypatch.delenv("SF_USERNAME", raising=False)
    with pytest.raises(RuntimeError, match="Missing required Salesforce credential: SF_USERNAME"):
        client.fetch_contacts()

def test_fetch_contacts_success(monkeypatch):
    monkeypatch.setenv("SF_USERNAME", "test@example.com")
    monkeypatch.setenv("SF_PASSWORD", "secret")
    monkeypatch.setenv("SF_SECURITY_TOKEN", "token123")
    
    mock_sf = MagicMock()
    fake_records = {
        "records": [
            {
                "Id": "SF001",
                "Name": "Alice Smith",
                "Email": "alice@example.com",
                "attributes": {"type": "Contact"}
            }
        ]
    }
    
    monkeypatch.setattr(client, "_build_client", lambda creds: mock_sf)
    monkeypatch.setattr(client, "_run_query", lambda sf, soql: fake_records)
    
    results = client.fetch_contacts()
    
    assert len(results) == 1
    assert results[0]["external_id"] == "SF001"
    assert results[0]["full_name"] == "Alice Smith"

def test_get_credentials_domain_logic(monkeypatch):
    monkeypatch.setenv("SF_USERNAME", "u")
    monkeypatch.setenv("SF_PASSWORD", "p")
    monkeypatch.setenv("SF_SECURITY_TOKEN", "t")
    
    monkeypatch.delenv("SF_DOMAIN", raising=False)
    assert client._get_credentials()["domain"] == "login"

    monkeypatch.setenv("SF_DOMAIN", "test")
    assert client._get_credentials()["domain"] == "test"