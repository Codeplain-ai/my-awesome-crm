import pytest
from unittest.mock import patch, MagicMock
from src.integrations.close import fetch_contacts

@patch.dict("os.environ", {"CLOSE_API_KEY": "test-key"})
@patch("httpx.Client.get")
def test_fetch_contacts_multi_page_and_skip_logic(mock_get):
    # Setup: 2 pages. 
    # Page 1: 1 good record, 1 bad record (missing ID)
    # Page 2: 1 good record
    
    page1 = {
        "data": [
            {"id": "c1", "name": "Good One"},
            {"name": "Bad One (No ID)"} 
        ],
        "has_more": True
    }
    page2 = {
        "data": [
            {"id": "c2", "name": "Good Two"}
        ],
        "has_more": False
    }
    
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: page1, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: page2, raise_for_status=lambda: None)
    ]
    
    contacts = fetch_contacts()
    
    # Should have 2 successfully mapped records
    assert len(contacts) == 2
    assert contacts[0]["external_id"] == "c1"
    assert contacts[1]["external_id"] == "c2"
    
    # Verify mock was called with correct skip params
    assert mock_get.call_count == 2
    # First call skip=0
    args0, kwargs0 = mock_get.call_args_list[0]
    assert kwargs0["params"]["_skip"] == 0
    # Second call skip=2 (total records in page 1 data)
    args1, kwargs1 = mock_get.call_args_list[1]
    assert kwargs1["params"]["_skip"] == 2

@patch.dict("os.environ", {"CLOSE_API_KEY": "test-key"})
@patch("httpx.Client.get")
def test_fetch_contacts_auth_failure(mock_get):
    mock_get.return_value = MagicMock(status_code=401)
    
    with pytest.raises(RuntimeError, match="authentication failed"):
        fetch_contacts()

@patch.dict("os.environ", {}, clear=True)
def test_fetch_contacts_missing_credentials():
    with pytest.raises(RuntimeError, match="CLOSE_API_KEY"):
        fetch_contacts()