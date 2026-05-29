import pytest
from unittest.mock import patch
from src.integrations.copper.client import fetch_contacts

def test_fetch_contacts_pagination(monkeypatch):
    monkeypatch.setenv("COPPER_API_KEY", "test-key")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")
    
    mock_page1 = [
        {"id": 1, "name": "User 1"},
        {"id": 2, "name": "User 2"}
    ]
    mock_page2 = [] # End of stream
    
    call_count = 0
    def mock_post(url, headers, json_data):
        nonlocal call_count
        call_count += 1
        assert json_data["page_number"] == call_count
        if call_count == 1:
            return mock_page1
        return mock_page2

    with patch("src.integrations.copper.client._post", side_effect=mock_post):
        results = list(fetch_contacts())
        
    assert len(results) == 2
    assert results[0]["external_id"] == "1"
    assert results[1]["external_id"] == "2"
    assert call_count == 2

def test_fetch_contacts_missing_creds(monkeypatch):
    monkeypatch.delenv("COPPER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="COPPER_API_KEY"):
        list(fetch_contacts())

def test_fetch_contacts_api_error(monkeypatch):
    monkeypatch.setenv("COPPER_API_KEY", "test-key")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")
    
    with patch("src.integrations.copper.client._post") as mocked:
        mocked.side_effect = RuntimeError("Copper API error: 500")
        with pytest.raises(RuntimeError, match="500"):
            list(fetch_contacts())