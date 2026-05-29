import pytest
from unittest.mock import patch
from src.integrations.pipedrive.client import fetch_contacts

@patch("src.integrations.pipedrive.client._get")
@patch.dict("os.environ", {
    "PIPEDRIVE_API_TOKEN": "fake-token",
    "PIPEDRIVE_COMPANY_DOMAIN": "test-co"
})
def test_fetch_contacts_pagination(mock_get):
    # Mock two pages of results
    mock_get.side_effect = [
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
    assert mock_get.call_count == 2

@patch.dict("os.environ", {}, clear=True)
def test_fetch_contacts_missing_token_raises():
    with pytest.raises(RuntimeError, match="Missing required environment variable: PIPEDRIVE_API_TOKEN"):
        fetch_contacts()

@patch.dict("os.environ", {"PIPEDRIVE_API_TOKEN": "token"}, clear=True)
def test_fetch_contacts_missing_domain_raises():
    with pytest.raises(RuntimeError, match="Missing required environment variable: PIPEDRIVE_COMPANY_DOMAIN"):
        fetch_contacts()

@patch("requests.get")
def test_get_indirection_error_handling(mock_requests_get):
    from src.integrations.pipedrive.client import _get
    
    mock_response = mock_requests_get.return_value
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.text = "Invalid Token"
    
    with pytest.raises(RuntimeError) as excinfo:
        _get("http://example.com", {})
    
    assert "401" in str(excinfo.value)
    assert "Invalid Token" in str(excinfo.value)