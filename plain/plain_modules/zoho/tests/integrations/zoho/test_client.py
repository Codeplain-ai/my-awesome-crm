import pytest
from unittest.mock import patch, MagicMock
from src.integrations.zoho.client import fetch_contacts

@patch("src.integrations.zoho.client._get_credentials")
@patch("src.integrations.zoho.client._refresh_access_token")
@patch("src.integrations.zoho.client._get_contacts_page")
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
    
    contacts = fetch_contacts()
    
    assert isinstance(contacts, list)
    assert len(contacts) == 2
    assert contacts[0]["external_id"] == "z1"
    assert contacts[1]["external_id"] == "z2"
    assert mock_fetch.call_count == 2

@patch("src.integrations.zoho.client._get_credentials")
@patch("src.integrations.zoho.client._refresh_access_token")
@patch("requests.get")
def test_fetch_contacts_error_handling(mock_get, mock_refresh, mock_creds):
    mock_creds.return_value = {
        "client_id": "cid", "client_secret": "sec", "refresh_token": "ref",
        "accounts_domain": "acc.com", "api_domain": "api.com"
    }
    mock_refresh.return_value = "token"
    
    # Simulate a 500 error from Zoho
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.ok = False
    mock_response.text = "Internal Server Error"
    mock_get.return_value = mock_response
    
    with pytest.raises(RuntimeError) as excinfo:
        fetch_contacts()
    
    assert "Status: 500" in str(excinfo.value)
    assert "URL: https://api.com/crm/v2/Contacts" in str(excinfo.value)
    assert "Body: Internal Server Error" in str(excinfo.value)

@patch("src.integrations.zoho.client.os.environ", {})
def test_fetch_contacts_missing_creds():
    with pytest.raises(RuntimeError, match="Missing required Zoho credential"):
        list(fetch_contacts())