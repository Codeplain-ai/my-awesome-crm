import pytest
from unittest.mock import patch
from src.integrations.sugarcrm.client import fetch_contacts

@patch.dict("os.environ", {
    "SUGARCRM_API_BASE": "https://test.sugarcrm.com/rest/v11",
    "SUGARCRM_USERNAME": "admin",
    "SUGARCRM_PASSWORD": "password"
})
@patch("src.integrations.sugarcrm.client._token_exchange")
@patch("src.integrations.sugarcrm.client._get_contacts_page")
def test_fetch_contacts_pagination(mock_get_page, mock_token, monkeypatch):
    mock_token.return_value = "fake-token"
    
    # Page 1
    mock_get_page.side_effect = [
        {
            "records": [{"id": "c1", "full_name": "Contact 1"}],
            "next_offset": 200
        },
        # Page 2 (last)
        {
            "records": [{"id": "c2", "full_name": "Contact 2"}],
            "next_offset": -1
        }
    ]

    contacts = fetch_contacts()
    assert isinstance(contacts, list)
    assert len(contacts) == 2
    assert contacts[0]["external_id"] == "c1"
    assert contacts[1]["external_id"] == "c2"
    assert mock_get_page.call_count == 2

@patch.dict("os.environ", {
    "SUGARCRM_API_BASE": "https://test.sugarcrm.com/rest/v11",
    "SUGARCRM_USERNAME": "admin",
    "SUGARCRM_PASSWORD": "password"
})
@patch("src.integrations.sugarcrm.client._token_exchange")
@patch("src.integrations.sugarcrm.client._get_contacts_page")
def test_fetch_contacts_empty(mock_get_page, mock_token):
    mock_token.return_value = "fake-token"
    mock_get_page.return_value = {"records": [], "next_offset": -1}

    contacts = fetch_contacts()
    assert len(contacts) == 0

def test_fetch_contacts_missing_creds():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing required SugarCRM credentials"):
            fetch_contacts()