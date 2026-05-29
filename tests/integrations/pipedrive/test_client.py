import pytest
from unittest.mock import patch
from src.integrations.pipedrive.client import fetch_contacts

@patch("src.integrations.pipedrive.client._request_page")
@patch.dict("os.environ", {
    "PIPEDRIVE_API_TOKEN": "fake-token",
    "PIPEDRIVE_COMPANY_DOMAIN": "test-co"
})
def test_fetch_contacts_pagination(mock_request):
    # Mock two pages of results
    mock_request.side_effect = [
        {
            "data": [{"id": 1, "name": "User 1"}],
            "additional_data": {"pagination": {"more_items_in_collection": True, "next_start": 1}}
        },
        {
            "data": [{"id": 2, "name": "User 2"}],
            "additional_data": {"pagination": {"more_items_in_collection": False}}
        }
    ]
    
    results = fetch_contacts()
    
    assert len(results) == 2
    assert results[0]["external_id"] == "1"
    assert results[1]["external_id"] == "2"
    assert mock_request.call_count == 2

@patch.dict("os.environ", {}, clear=True)
def test_fetch_contacts_missing_env_raises():
    with pytest.raises(RuntimeError, match="Missing required environment variable"):
        fetch_contacts()