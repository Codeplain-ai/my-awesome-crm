import pytest
from unittest.mock import patch
from src.integrations.copper.client import fetch_contacts

def test_fetch_contacts_pagination_exact_multiple(monkeypatch):
    """Test pagination where the last page is empty."""
    monkeypatch.setenv("COPPER_API_KEY", "test-key")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")
    
    # Assume page_size is 200
    mock_page1 = [{"id": i, "name": f"User {i}"} for i in range(200)]
    mock_page2 = []
    
    calls = []
    def mock_search(url, api_key, user_email, body):
        calls.append(body)
        if body["page_number"] == 1:
            return mock_page1
        return mock_page2

    with patch("src.integrations.copper.client._search", side_effect=mock_search):
        results = list(fetch_contacts())
        
    assert len(results) == 200
    assert len(calls) == 2
    assert calls[0]["page_number"] == 1
    assert calls[1]["page_number"] == 2

def test_fetch_contacts_pagination_partial_last_page(monkeypatch):
    """Test pagination where the last page is partially full."""
    monkeypatch.setenv("COPPER_API_KEY", "test-key")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")
    
    mock_page1 = [{"id": 1, "name": "User 1"}] # 1 item < 200 page_size
    
    calls = []
    def mock_search(url, api_key, user_email, body):
        calls.append(body)
        return mock_page1

    with patch("src.integrations.copper.client._search", side_effect=mock_search):
        results = list(fetch_contacts())
        
    assert len(results) == 1
    assert len(calls) == 1 # Should stop immediately after partial page

def test_fetch_contacts_missing_creds(monkeypatch):
    monkeypatch.delenv("COPPER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="COPPER_API_KEY"):
        list(fetch_contacts())

def test_fetch_contacts_api_error(monkeypatch):
    monkeypatch.setenv("COPPER_API_KEY", "test-key")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")
    
    with patch("src.integrations.copper.client._search") as mocked:
        mocked.side_effect = RuntimeError("Copper API error: 500 - Internal Server Error URL: ...")
        with pytest.raises(RuntimeError, match="500"):
            list(fetch_contacts())