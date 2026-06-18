import pytest
from unittest.mock import patch, MagicMock
from src.integrations.salesforce import fetch_contacts

@pytest.fixture
def sf_env(monkeypatch):
    monkeypatch.setenv("SALESFORCE_ENDPOINT", "https://test.salesforce.com")
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "client-id")
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "client-secret")

def test_fetch_contacts_multi_page(sf_env):
    """Tests multi-page pagination and token acquisition."""
    
    def mock_request(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        
        if "/services/oauth2/token" in str(url):
            mock_resp.json.return_value = {
                "access_token": "fake-token",
                "instance_url": "https://instance.salesforce.com"
            }
        elif "query" in url and "next_page" not in url:
            # First page
            mock_resp.json.return_value = {
                "totalSize": 3,
                "done": False,
                "nextRecordsUrl": "/services/data/v60.0/query/next_page",
                "records": [
                    {"Id": "001", "Name": "Contact 1"},
                    {"Id": "002", "Name": "Contact 2"}
                ]
            }
        elif "next_page" in url:
            # Second (final) page
            mock_resp.json.return_value = {
                "totalSize": 3,
                "done": True,
                "records": [
                    {"Id": "003", "Name": "Contact 3"}
                ]
            }
        return mock_resp

    with patch("httpx.post", side_effect=mock_request), \
         patch("httpx.get", side_effect=mock_request):
        
        results = fetch_contacts()
        
        assert len(results) == 3
        assert results[0]["external_id"] == "001"
        assert results[1]["external_id"] == "002"
        assert results[2]["external_id"] == "003"

def test_fetch_contacts_skip_malformed(sf_env, caplog):
    """Tests that a ValueError in mapping skips the record and continues."""
    
    auth_resp = MagicMock(status_code=200)
    auth_resp.json.return_value = {"access_token": "t", "instance_url": "https://i"}
    
    query_resp = MagicMock(status_code=200)
    query_resp.json.return_value = {
        "done": True,
        "records": [
            {"Id": "GOOD1", "Name": "Valid User"},
            {"Id": "BAD1"},  # Missing Name -> ValueError
            {"Id": "GOOD2", "Name": "Another Valid"}
        ]
    }

    with patch("httpx.post", return_value=auth_resp), \
         patch("httpx.get", return_value=query_resp):
        
        results = fetch_contacts()
        
        assert len(results) == 2
        assert results[0]["external_id"] == "GOOD1"
        assert results[1]["external_id"] == "GOOD2"
        assert "Skipping malformed Salesforce record BAD1" in caplog.text

def test_missing_credentials_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("SALESFORCE_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError, match="SALESFORCE_ENDPOINT"):
        fetch_contacts()

def test_auth_failure_raises_runtime_error(sf_env):
    auth_resp = MagicMock(status_code=401, text="Unauthorized")
    with patch("httpx.post", return_value=auth_resp):
        with pytest.raises(RuntimeError, match="authentication failed"):
            fetch_contacts()