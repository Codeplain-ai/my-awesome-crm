import pytest
import os
from unittest.mock import MagicMock, patch
from src.integrations.pipedrive import fetch

@patch("httpx.Client.get")
def test_fetch_pagination(mock_get):
    # Setup environment
    os.environ["PIPEDRIVE_API_TOKEN"] = "fake-token"
    os.environ["PIPEDRIVE_COMPANY_DOMAIN"] = "test-co"

    # Mock responses for 2 pages
    page1 = {
        "success": True,
        "data": [{"id": 1, "name": "Person 1"}],
        "additional_data": {
            "pagination": {
                "more_items_in_collection": True,
                "next_start": 1
            }
        }
    }
    page2 = {
        "success": True,
        "data": [{"id": 2, "name": "Person 2"}],
        "additional_data": {
            "pagination": {
                "more_items_in_collection": False
            }
        }
    }

    mock_response1 = MagicMock()
    mock_response1.json.return_value = page1
    mock_response1.status_code = 200
    
    mock_response2 = MagicMock()
    mock_response2.json.return_value = page2
    mock_response2.status_code = 200

    mock_get.side_effect = [mock_response1, mock_response2]

    # Run
    get_stored = MagicMock(return_value=[])
    records = fetch(get_stored)

    # Verify
    assert len(records) == 2
    assert records[0]["data"]["external_id"] == "1"
    assert records[1]["data"]["external_id"] == "2"
    assert mock_get.call_count == 2
    
    # Check if second call used the next_start
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["start"] == 1

def test_fetch_missing_creds():
    with patch.dict(os.environ, {}, clear=True):
        get_stored = MagicMock()
        # Requirement: raise RuntimeError with the name of the missing key
        with pytest.raises(RuntimeError, match="PIPEDRIVE_API_TOKEN"):
            fetch(get_stored)

def test_fetch_api_error_raises():
    os.environ["PIPEDRIVE_API_TOKEN"] = "token"
    os.environ["PIPEDRIVE_COMPANY_DOMAIN"] = "domain"
    
    with patch("httpx.Client.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": False, "error": "Invalid token"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        get_stored = MagicMock()
        with pytest.raises(RuntimeError, match="Pipedrive API error: Invalid token"):
            fetch(get_stored)