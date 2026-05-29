import pytest
from unittest.mock import MagicMock, patch
from src.integrations.hubspot.client import fetch_contacts

def test_fetch_contacts_missing_creds():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="HUBSPOT_ACCESS_TOKEN"):
            list(fetch_contacts())

def test_fetch_contacts_pagination(monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token")
    
    # Mock Response Objects
    mock_contact = MagicMock()
    mock_contact.to_dict.return_value = {
        "id": "hs1",
        "properties": {"firstname": "Alice", "email": "alice@hub.com"}
    }
    
    mock_page_1 = MagicMock()
    mock_page_1.results = [mock_contact]
    mock_page_1.paging.next.after = "cursor2"
    
    mock_page_2 = MagicMock()
    mock_page_2.results = [mock_contact]
    mock_page_2.paging = None  # End of pagination
    
    mock_fetch = MagicMock(side_effect=[mock_page_1, mock_page_2])
    
    with patch("src.integrations.hubspot.client._fetch_page", mock_fetch):
        results = list(fetch_contacts())
        
        assert len(results) == 2
        assert results[0]["external_id"] == "hs1"
        assert mock_fetch.call_count == 2
        # Check cursor passed correctly on second call
        assert mock_fetch.call_args_list[1][0][1] == "cursor2"

def test_fetch_contacts_api_error():
    with patch.dict("os.environ", {"HUBSPOT_ACCESS_TOKEN": "token"}):
        with patch("src.integrations.hubspot.client._fetch_page", side_effect=Exception("API Down")):
            with pytest.raises(RuntimeError, match="HubSpot API request failed: API Down"):
                list(fetch_contacts())