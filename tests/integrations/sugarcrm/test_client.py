import pytest
from unittest.mock import patch
import os
from src.integrations.sugarcrm.client import fetch_contacts

@patch.dict(os.environ, {
    "SUGARCRM_API_BASE": "https://test.sugar.crm/rest/v11",
    "SUGARCRM_USERNAME": "admin",
    "SUGARCRM_PASSWORD": "password"
})
@patch("src.integrations.sugarcrm.client._token_exchange")
@patch("src.integrations.sugarcrm.client._get_contacts_page")
def test_fetch_contacts_pagination_logic(mock_get_page, mock_token):
    mock_token.return_value = "fake-session-id"
    
    # Mock two pages of results
    mock_get_page.side_effect = [
        {
            "records": [{"id": "c1", "full_name": "First Contact"}],
            "next_offset": 1
        },
        {
            "records": [{"id": "c2", "full_name": "Second Contact"}],
            "next_offset": -1
        }
    ]

    contacts = fetch_contacts()
    
    assert len(contacts) == 2
    assert contacts[0]["external_id"] == "c1"
    assert contacts[1]["external_id"] == "c2"
    assert mock_get_page.call_count == 2
    
    # Verify the offset was passed correctly
    mock_get_page.assert_any_call("https://test.sugar.crm/rest/v11", "fake-session-id", 0)
    mock_get_page.assert_any_call("https://test.sugar.crm/rest/v11", "fake-session-id", 1)

@patch.dict(os.environ, {
    "SUGARCRM_API_BASE": "https://test.sugar.crm/rest/v11",
    "SUGARCRM_USERNAME": "admin",
    "SUGARCRM_PASSWORD": "password"
})
@patch("src.integrations.sugarcrm.client._token_exchange")
@patch("src.integrations.sugarcrm.client._get_contacts_page")
def test_fetch_contacts_empty_results(mock_get_page, mock_token):
    mock_token.return_value = "token"
    mock_get_page.return_value = {"records": [], "next_offset": -1}

    contacts = fetch_contacts()
    assert contacts == []

def test_fetch_contacts_raises_on_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing required SugarCRM credentials"):
            fetch_contacts()