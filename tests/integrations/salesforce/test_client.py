import pytest
from unittest.mock import MagicMock
from src.integrations.salesforce import client

def test_fetch_contacts_missing_credentials(monkeypatch):
    """Ensure fetch_contacts raises RuntimeError if environment variables are missing."""
    monkeypatch.delenv("SF_USERNAME", raising=False)
    
    with pytest.raises(RuntimeError, match="Missing required Salesforce credential: SF_USERNAME"):
        client.fetch_contacts()

def test_fetch_contacts_success(monkeypatch):
    """Test successful fetch and mapping using mocks for Salesforce API."""
    # 1. Setup Environment
    monkeypatch.setenv("SF_USERNAME", "test@example.com")
    monkeypatch.setenv("SF_PASSWORD", "secret")
    monkeypatch.setenv("SF_SECURITY_TOKEN", "token123")
    
    # 2. Mock the client and query execution
    mock_sf = MagicMock()
    def mock_build_client(creds):
        return mock_sf
    
    fake_records = {
        "records": [
            {
                "Id": "SF001",
                "Name": "Alice Smith",
                "Email": "alice@example.com",
                "attributes": {"type": "Contact"}
            },
            {
                "Id": "SF002",
                "FirstName": "Bob",
                "LastName": "Jones",
                "Account": {"Name": "Jones Ltd"},
                "attributes": {"type": "Contact"}
            }
        ]
    }
    
    def mock_run_query(sf, soql):
        assert "FROM Contact" in soql
        return fake_records

    monkeypatch.setattr(client, "_build_client", mock_build_client)
    monkeypatch.setattr(client, "_run_query", mock_run_query)
    
    # 3. Execute
    results = client.fetch_contacts()
    
    # 4. Assertions
    assert len(results) == 2
    
    assert results[0]["external_id"] == "SF001"
    assert results[0]["full_name"] == "Alice Smith"
    assert results[0]["primary_email"] == "alice@example.com"
    
    assert results[1]["external_id"] == "SF002"
    assert results[1]["full_name"] == "Bob Jones"
    assert results[1]["company_name"] == "Jones Ltd"
    assert results[1]["primary_email"] is None

def test_get_credentials_domain_default(monkeypatch):
    """Verify that SF_DOMAIN defaults to 'login'."""
    monkeypatch.setenv("SF_USERNAME", "u")
    monkeypatch.setenv("SF_PASSWORD", "p")
    monkeypatch.setenv("SF_SECURITY_TOKEN", "t")
    monkeypatch.delenv("SF_DOMAIN", raising=False)
    
    creds = client._get_credentials()
    assert creds["domain"] == "login"

    monkeypatch.setenv("SF_DOMAIN", "test")
    creds = client._get_credentials()
    assert creds["domain"] == "test"