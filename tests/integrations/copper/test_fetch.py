import pytest
import os
from unittest.mock import patch, MagicMock
import src.integrations.copper
from src.integrations.copper import fetch


def test_integration_exports():
    """Verify the integration exports the required host interface."""
    assert hasattr(src.integrations.copper, "fetch")
    assert callable(src.integrations.copper.fetch)
    assert hasattr(src.integrations.copper, "DATA_TYPE")
    assert src.integrations.copper.DATA_TYPE == "contact"
    assert "fetch" in src.integrations.copper.__all__
    assert "DATA_TYPE" in src.integrations.copper.__all__


@patch("httpx.Client")
@patch.dict("os.environ", {"COPPER_API_KEY": "test_key", "COPPER_USER_EMAIL": "test@example.com"})
def test_fetch_pagination_multi_page(mock_client_class):
    """Verifies that fetch correctly iterates through pages until a partial page is found."""
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Page 1: 200 records (Full)
    page1 = [{"id": i} for i in range(200)]
    # Page 2: 10 records (Partial)
    page2 = [{"id": i + 200} for i in range(10)]
    
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = page1
    
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = page2
    
    mock_client.post.side_effect = [resp1, resp2]
    
    # get_stored is ignored by Copper integration, but required by signature
    results = fetch(lambda x: [])
    
    assert len(results) == 210
    assert mock_client.post.call_count == 2
    
    # Verify request body for second page
    last_call_args = mock_client.post.call_args_list[1]
    assert last_call_args.kwargs["json"]["page_number"] == 2

@patch.dict("os.environ", {}, clear=True)
def test_fetch_missing_api_key():
    with pytest.raises(RuntimeError, match="Missing required Copper credential: COPPER_API_KEY"):
        fetch(lambda x: [])

@patch.dict("os.environ", {"COPPER_API_KEY": "key"}, clear=True)
def test_fetch_missing_user_email():
    with pytest.raises(RuntimeError, match="Missing required Copper credential: COPPER_USER_EMAIL"):
        fetch(lambda x: [])

@patch("httpx.Client")
@patch.dict("os.environ", {"COPPER_API_KEY": "k", "COPPER_USER_EMAIL": "e"})
def test_fetch_api_error_propagation(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    error_resp = MagicMock()
    error_resp.status_code = 401
    error_resp.json.return_value = {"message": "Invalid API Key"}
    error_resp.content = b'{"message": "Invalid API Key"}'
    mock_client.post.return_value = error_resp
    
    with pytest.raises(RuntimeError, match="Copper API error \(status 401\): Invalid API Key"):
        fetch(lambda x: [])