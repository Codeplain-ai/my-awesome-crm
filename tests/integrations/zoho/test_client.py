import pytest
from unittest.mock import patch, MagicMock
from src.integrations.zoho.client import fetch_contacts

@patch("src.integrations.zoho.client._get_credentials")
@patch("src.integrations.zoho.client._refresh_access_token")
@patch("src.integrations.zoho.client._fetch_page")
def test_fetch_contacts_flow(mock_fetch, mock_refresh, mock_creds):
    # Setup mocks
    mock_creds.return_value = {
        "client_id": "cid", "client_secret": "sec", "refresh_token": "ref",
        "accounts_domain": "acc.com", "api_domain": "api.com"
    }
    mock_refresh.return_value = "fake_access_token"
    
    # Mock two pages of results
    mock_fetch.side_effect = [
        {
            "data": [{"id": "z1", "Full_Name": "User One"}],
            "info": {"more_records": True}
        },
        {
            "data": [{"id": "z2", "Full_Name": "User Two"}],
            "info": {"more_records": False}
        }
    ]
    
    contacts = list(fetch_contacts())
    
    assert len(contacts) == 2
    assert contacts[0]["external_id"] == "z1"
    assert contacts[1]["external_id"] == "z2"
    assert mock_fetch.call_count == 2

@patch("src.integrations.zoho.client.os.environ", {})
def test_fetch_contacts_missing_creds():
    with pytest.raises(RuntimeError, match="Missing required Zoho credential"):
        list(fetch_contacts())