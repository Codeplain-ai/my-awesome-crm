import pytest
from unittest.mock import MagicMock, patch
from src.integrations.hubspot.client import fetch_contacts

def test_fetch_contacts_missing_creds():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="HUBSPOT_ACCESS_TOKEN"):
            fetch_contacts()

def test_fetch_contacts_pagination(monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token")
    
    # Mock return dict for _to_dict
    mock_raw_contact = {"id": "hs1", "properties": {"firstname": "Alice", "email": "alice@hub.com"}}
    
    mock_page_1 = MagicMock()
    mock_page_1.results = ["obj1"]
    mock_page_1.paging.next.after = "cursor2"
    
    mock_page_2 = MagicMock()
    mock_page_2.results = ["obj2"]
    mock_page_2.paging = None  # End of pagination
    
    mock_get_page = MagicMock(side_effect=[mock_page_1, mock_page_2])
    mock_to_dict = MagicMock(return_value=mock_raw_contact)
    
    # Patch the indirection points in the client module
    with patch("src.integrations.hubspot.client._get_page", mock_get_page):
        with patch("src.integrations.hubspot.client._to_dict", mock_to_dict):
            results = fetch_contacts()
            
            assert isinstance(results, list)
            assert len(results) == 2
            assert results[0]["external_id"] == "hs1"
            assert mock_get_page.call_count == 2
            
            # Check cursor passed correctly on second call
            # call_args is (args, kwargs). [0] is args, [1] is 'after' parameter
            assert mock_get_page.call_args_list[1][0][1] == "cursor2"
            
            # Check properties list was passed
            assert "firstname" in mock_get_page.call_args_list[0][0][2]

def test_fetch_contacts_api_error():
    with patch.dict("os.environ", {"HUBSPOT_ACCESS_TOKEN": "token"}):
        with patch("src.integrations.hubspot.client._get_page", side_effect=Exception("API Down")):
            with pytest.raises(RuntimeError, match="HubSpot API request failed: API Down"):
                fetch_contacts()