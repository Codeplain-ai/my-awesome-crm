import pytest
from unittest.mock import patch
import src.integrations.dynamics
from src.integrations.dynamics import client

def test_integration_discovery_export():
    """Verify the discovery contract: fetch_contacts must be available at package root."""
    assert hasattr(src.integrations.dynamics, "fetch_contacts")
    assert callable(src.integrations.dynamics.fetch_contacts)

def test_fetch_contacts_missing_creds(monkeypatch):
    monkeypatch.delenv("DYNAMICS_TENANT_ID", raising=False)
    with pytest.raises(RuntimeError, match="DYNAMICS_TENANT_ID"):
        client.fetch_contacts()

def test_fetch_contacts_pagination_and_skip(monkeypatch, caplog):
    monkeypatch.setenv("DYNAMICS_TENANT_ID", "tenant")
    monkeypatch.setenv("DYNAMICS_CLIENT_ID", "client")
    monkeypatch.setenv("DYNAMICS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("DYNAMICS_RESOURCE_URL", "https://crm.dynamics.com")

    # Page 1: 1 Good, 1 Bad (no name)
    page1 = {
        "value": [
            {"contactid": "ok1", "fullname": "Good One"},
            {"contactid": "bad1"} # Missing name triggers ValueError in mapping
        ],
        "@odata.nextLink": "https://crm.dynamics.com/page2"
    }
    # Page 2: 1 Good
    page2 = {
        "value": [
            {"contactid": "ok2", "fullname": "Good Two"}
        ]
    }

    def mock_get_json(url, token):
        if "page2" in url:
            return page2
        return page1

    with patch("src.integrations.dynamics.client._acquire_token", return_value="fake-token"), \
         patch("src.integrations.dynamics.client._get_json", side_effect=mock_get_json):
        
        results = client.fetch_contacts()
        
        assert len(results) == 2
        assert results[0]["external_id"] == "ok1"
        assert results[1]["external_id"] == "ok2"
        assert "Skipping malformed Dynamics contact bad1" in caplog.text

def test_acquire_token_calls_correct_v2_endpoint(monkeypatch):
    creds = {
        "DYNAMICS_TENANT_ID": "my-tenant",
        "DYNAMICS_CLIENT_ID": "my-client",
        "DYNAMICS_CLIENT_SECRET": "my-secret",
        "DYNAMICS_RESOURCE_URL": "https://org.crm.dynamics.com"
    }
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"access_token": "secret-token"}
        token = client._acquire_token(creds)
        
        assert token == "secret-token"
        args, kwargs = mock_post.call_args
        assert args[0] == "https://login.microsoftonline.com/my-tenant/oauth2/v2.0/token"
        assert kwargs["data"]["scope"] == "https://org.crm.dynamics.com/.default"