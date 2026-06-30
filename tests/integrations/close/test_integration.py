import pytest
from unittest.mock import MagicMock, patch
from src.integrations.close import fetch

@patch("src.integrations.close.httpx.Client")
@patch.dict("os.environ", {"CLOSE_API_KEY": "test_key"})
def test_fetch_pagination(mock_client_class):
    # Mock responses for two pages
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Page 1
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "data": [{"id": "c1", "name": "User 1"}],
        "has_more": True
    }
    
    # Page 2
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "data": [{"id": "c2", "name": "User 2"}],
        "has_more": False
    }
    
    mock_client.get.side_effect = [resp1, resp2]
    
    get_stored = MagicMock(return_value=[])
    results = fetch(get_stored)
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "c1"
    assert results[1]["data"]["external_id"] == "c2"
    assert mock_client.get.call_count == 2

@patch.dict("os.environ", {}, clear=True)
def test_fetch_missing_credentials():
    # Verify strict error message requirement
    with pytest.raises(RuntimeError, match="Missing required environment variable: CLOSE_API_KEY"):
        fetch(lambda x: [])

@patch("src.integrations.close.httpx.Client")
@patch.dict("os.environ", {"CLOSE_API_KEY": "test_key"})
def test_fetch_auth_error(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    resp = MagicMock()
    resp.status_code = 401
    resp.text = "Unauthorized"
    mock_client.get.return_value = resp
    
    with pytest.raises(RuntimeError, match="Authentication failed"):
        fetch(lambda x: [])

def test_public_api_interface():
    """Verify the integration exports the expected host-discovery interface."""
    import src.integrations.close as close_pkg
    assert hasattr(close_pkg, "fetch")
    assert callable(close_pkg.fetch)
    assert hasattr(close_pkg, "DATA_TYPE")
    assert close_pkg.DATA_TYPE == "contact"
    assert "fetch" in close_pkg.__all__
    assert "DATA_TYPE" in close_pkg.__all__