import pytest
from unittest.mock import patch
from src.integrations.close.client import fetch_contacts

@patch("src.integrations.close.client._get")
@patch.dict("os.environ", {"CLOSE_API_KEY": "sk_test_key"})
def test_fetch_contacts_pagination(mock_get_internal):
    # Mock first page and second page
    mock_get_internal.side_effect = [
        {
            "data": [{"id": "c1", "name": "Contact 1"}],
            "has_more": True
        },
        {
            "data": [{"id": "c2", "name": "Contact 2"}],
            "has_more": False
        }
    ]
    
    contacts = fetch_contacts()
    
    assert len(contacts) == 2
    assert contacts[0]["external_id"] == "c1"
    assert contacts[1]["external_id"] == "c2"
    assert mock_get_internal.call_count == 2
    
    # Check that skip parameter was incremented correctly based on data length
    # _get(url, api_key, params) -> params is the 3rd argument (index 2)
    args, _ = mock_get_internal.call_args_list[1]
    assert args[2]["_skip"] == 1

@patch("src.integrations.close.client._get")
@patch.dict("os.environ", {"CLOSE_API_KEY": "sk_test_key"})
def test_fetch_contacts_http_error(mock_get_internal):
    mock_get_internal.side_effect = RuntimeError("Close API request failed with status 401")
    
    with pytest.raises(RuntimeError, match="401"):
        fetch_contacts()

@patch.dict("os.environ", {}, clear=True)
def test_fetch_contacts_no_creds():
    with pytest.raises(RuntimeError, match="CLOSE_API_KEY"):
        fetch_contacts()