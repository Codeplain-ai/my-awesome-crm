import pytest
from unittest.mock import patch, MagicMock
from src.integrations.nimble import fetch

@patch("src.integrations.nimble.client.httpx.Client")
@patch("src.integrations.nimble.client.os.environ.get")
def test_fetch_pagination_and_aggregation(mock_env, mock_client_class):
    # Setup
    mock_env.return_value = "fake-token"
    mock_client = mock_client_class.return_value.__enter__.return_value
    
    # Page 1 response
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "resources": [{"id": "p1", "fields": {"first name": [{"value": "P1"}]}}],
        "meta": {"page": 1, "pages": 2, "per_page": 1, "total": 2}
    }
    
    # Page 2 response
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "resources": [{"id": "p2", "fields": {"first name": [{"value": "P2"}]}}],
        "meta": {"page": 2, "pages": 2, "per_page": 1, "total": 2}
    }
    
    mock_client.get.side_effect = [resp1, resp2]
    
    # Execute
    results = fetch(get_stored=lambda x: [])
    
    # Assert
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "p1"
    assert results[1]["data"]["external_id"] == "p2"
    assert mock_client.get.call_count == 2

@patch("src.integrations.nimble.client.httpx.Client")
@patch("src.integrations.nimble.client.os.environ.get")
def test_fetch_skip_and_log_policy(mock_env, mock_client_class):
    mock_env.return_value = "fake-token"
    mock_client = mock_client_class.return_value.__enter__.return_value
    
    # Return one record that will be forced to cause a mapping error and one valid one
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.json.return_value = {
        "resources": [
            {"id": "bad", "fields": {}},
            {"id": "good", "fields": {"first name": [{"value": "Good"}]}}
        ],
        "meta": {"page": 1, "pages": 1, "per_page": 2, "total": 2}
    }
    
    # Force a ValueError for the first record
    with patch("src.integrations.nimble.map_contact") as mock_map:
        mock_map.side_effect = [ValueError("Simulated mapping error"), {"full_name": "Good"}]

        results = fetch(get_stored=lambda x: [])
        
        # Requirement: A skipped record never aborts the batch.
        assert len(results) == 1
        assert results[0]["data"]["full_name"] == "Good"

@patch("src.integrations.nimble.client.os.environ.get")
def test_fetch_raises_runtime_error_on_missing_token(mock_env):
    # Setup: Return empty string
    mock_env.return_value = ""
    
    with pytest.raises(RuntimeError) as excinfo:
        fetch(get_stored=lambda x: [])
    
    # Requirement: Raises naming the env var key.
    assert "NIMBLE_ACCESS_TOKEN" in str(excinfo.value)