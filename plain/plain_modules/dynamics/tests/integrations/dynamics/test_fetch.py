import pytest
from unittest.mock import patch, MagicMock
from src.integrations.dynamics import fetch, DATA_TYPE

def test_integration_exports():
    """Verify the integration exports the expected public API for discovery."""
    import src.integrations.dynamics as dynamics
    assert hasattr(dynamics, "fetch")
    assert callable(dynamics.fetch)
    assert hasattr(dynamics, "DATA_TYPE")
    assert dynamics.DATA_TYPE == "contact"
    if hasattr(dynamics, "__all__"):
        assert "fetch" in dynamics.__all__
        assert "DATA_TYPE" in dynamics.__all__

@patch("src.integrations.dynamics.DynamicsClient")
def test_fetch_orchestration(mock_client_class):
    mock_instance = mock_client_class.return_value
    mock_instance.list_contacts.return_value = [
        {"contactid": "c1", "fullname": "One"},
        {"contactid": "c2", "fullname": "Two"}
    ]
    
    def get_stored(t): return []
    
    results = fetch(get_stored)
    
    assert len(results) == 2
    assert results[0]["data_type"] == "contact"
    assert results[0]["data"]["external_id"] == "c1"
    assert results[1]["data"]["external_id"] == "c2"

@patch("src.integrations.dynamics.client.httpx.Client")
def test_client_pagination(mock_client_class):
    from src.integrations.dynamics.client import DynamicsClient
    import os

    # Setup env
    with patch.dict(os.environ, {
        "DYNAMICS_ENDPOINT": "https://test.crm.com",
        "DYNAMICS_TENANT_ID": "t1",
        "DYNAMICS_CLIENT_ID": "c1",
        "DYNAMICS_CLIENT_SECRET": "s1"
    }):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Mock Token response
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "abc"}
        
        # Mock Page 1
        mock_p1_resp = MagicMock()
        mock_p1_resp.status_code = 200
        mock_p1_resp.json.return_value = {
            "value": [{"contactid": "1"}],
            "@odata.nextLink": "https://test.crm.com/api/page2"
        }
        
        # Mock Page 2
        mock_p2_resp = MagicMock()
        mock_p2_resp.status_code = 200
        mock_p2_resp.json.return_value = {
            "value": [{"contactid": "2"}]
        }
        
        mock_client.post.return_value = mock_token_resp
        mock_client.get.side_effect = [mock_p1_resp, mock_p2_resp]
        
        client = DynamicsClient()
        records = client.list_contacts()
        
        assert len(records) == 2
        assert records[0]["contactid"] == "1"
        assert records[1]["contactid"] == "2"
        assert mock_client.get.call_count == 2

def test_missing_env_vars():
    from src.integrations.dynamics.client import DynamicsClient
    import os
    with patch.dict(os.environ, clear=True):
        with pytest.raises(RuntimeError) as exc:
            DynamicsClient()
        assert "DYNAMICS_ENDPOINT" in str(exc.value)