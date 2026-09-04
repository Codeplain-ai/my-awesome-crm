import pytest
from unittest.mock import MagicMock, patch, ANY
from src.integrations.sugarcrm import fetch

@patch("httpx.Client")
@patch("os.environ.get")
def test_fetch_pagination_and_mapping(mock_env, mock_client_class):
    # Setup environment mocks
    mock_env.side_effect = lambda k, default=None: {
        "SUGARCRM_USERNAME": "admin",
        "SUGARCRM_PASSWORD": "password",
        "SUGARCRM_ENDPOINT": "https://test.sugar.com",
        "SUGARCRM_CLIENT_ID": "sugar"
    }.get(k, default)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Mock token response
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "fake-token"}
    
    # Mock data pages
    # Page 1 has next_offset=2
    mock_page1 = MagicMock()
    mock_page1.status_code = 200
    mock_page1.json.return_value = {
        "records": [{"id": "rec1", "full_name": "Alpha"}],
        "next_offset": 2
    }
    
    # Page 2 has next_offset=-1
    mock_page2 = MagicMock()
    mock_page2.status_code = 200
    mock_page2.json.return_value = {
        "records": [{"id": "rec2", "full_name": "Beta"}],
        "next_offset": -1
    }

    mock_client.post.return_value = mock_token_resp
    mock_client.get.side_effect = [mock_page1, mock_page2]

    get_stored = MagicMock(return_value=[])
    
    # Execute
    results = fetch(get_stored)

    # Assertions
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "rec1"
    assert results[1]["data"]["external_id"] == "rec2"
    
    # Verify token acquisition was called
    mock_client.post.assert_called_with("/oauth2/token", json=ANY)
    # Verify GET was called twice (pagination)
    assert mock_client.get.call_count == 2

@patch("os.environ.get")
def test_fetch_missing_credentials_raises_runtime_error(mock_env):
    """Verify that missing required env vars raises RuntimeError."""
    mock_env.side_effect = lambda k, default=None: {
        "SUGARCRM_USERNAME": "admin",
        # SUGARCRM_PASSWORD is missing
        "SUGARCRM_ENDPOINT": "https://test.sugar.com",
        "SUGARCRM_CLIENT_ID": "sugar"
    }.get(k, default)

    get_stored = MagicMock()
    with pytest.raises(RuntimeError) as excinfo:
        fetch(get_stored)
    
    assert "SUGARCRM_PASSWORD" in str(excinfo.value)

@patch("httpx.Client")
@patch("os.environ.get")
def test_fetch_skip_and_log_policy(mock_env, mock_client_class):
    """Verify that a record causing a mapping error is skipped."""
    mock_env.side_effect = lambda k, default=None: {
        "SUGARCRM_USERNAME": "admin",
        "SUGARCRM_PASSWORD": "password",
        "SUGARCRM_ENDPOINT": "https://test.sugar.com",
        "SUGARCRM_CLIENT_ID": "sugar"
    }.get(k, default)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_token_resp = MagicMock(status_code=200)
    mock_token_resp.json.return_value = {"access_token": "fake-token"}
    mock_client.post.return_value = mock_token_resp

    # Page with one valid record and one record that will trigger a skip
    mock_page = MagicMock(status_code=200)
    mock_page.json.return_value = {
        "records": [
            {"id": "valid", "full_name": "Valid Name"},
            {"id": "broken", "full_name": "Trigger Error"}
        ],
        "next_offset": -1
    }
    mock_client.get.return_value = mock_page

    get_stored = MagicMock()

    # Patch map_contact to raise ValueError for the "broken" record.
    # We patch it in the namespace where it is consumed (src.integrations.sugarcrm).
    with patch("src.integrations.sugarcrm.map_contact") as mock_map:
        mock_map.side_effect = lambda rec: (
            {"external_id": rec["id"]} if rec["id"] == "valid" else exec('raise(ValueError("Test Skip"))')
        )
        
        results = fetch(get_stored)
        
        assert len(results) == 1
        assert results[0]["data"]["external_id"] == "valid"