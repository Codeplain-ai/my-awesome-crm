import pytest
from unittest.mock import patch, MagicMock
from src.integrations.close.client import fetch_contacts

@patch("src.integrations.close.client.requests.get")
@patch.dict("os.environ", {"CLOSE_API_KEY": "sk_test_key"})
def test_fetch_contacts_pagination(mock_get):
    # Mock first page
    mock_resp_1 = MagicMock()
    mock_resp_1.ok = True
    mock_resp_1.json.return_value = {
        "data": [{"id": "c1", "name": "Contact 1"}],
        "has_more": True
    }
    
    # Mock second page
    mock_resp_2 = MagicMock()
    mock_resp_2.ok = True
    mock_resp_2.json.return_value = {
        "data": [{"id": "c2", "name": "Contact 2"}],
        "has_more": False
    }
    
    mock_get.side_effect = [mock_resp_1, mock_resp_2]
    
    contacts = list(fetch_contacts())
    
    assert len(contacts) == 2
    assert contacts[0]["external_id"] == "c1"
    assert contacts[1]["external_id"] == "c2"
    assert mock_get.call_count == 2
    
    # Check that skip parameter was incremented
    args, kwargs = mock_get.call_args_list[1]
    assert kwargs["params"]["_skip"] == 1

@patch.dict("os.environ", {}, clear=True)
def test_fetch_contacts_no_creds():
    with pytest.raises(RuntimeError, match="CLOSE_API_KEY"):
        list(fetch_contacts())