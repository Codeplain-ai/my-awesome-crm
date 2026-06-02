import pytest
from src.integrations.streak import client

def test_fetch_contacts_missing_creds(monkeypatch):
    monkeypatch.delenv("STREAK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="STREAK_API_KEY"):
        list(client.fetch_contacts())

def test_fetch_contacts_success(monkeypatch):
    monkeypatch.setenv("STREAK_API_KEY", "test-key")
    
    mock_data = [
        {
            "key": "k1",
            "fullName": "Streak User",
            "emailAddresses": ["user@streak.com"]
        }
    ]
    
    def mock_get(url, api_key, params):
        assert api_key == "test-key"
        assert "/contacts" in url
        assert params["limit"] == 100
        return mock_data

    monkeypatch.setattr(client, "_get", mock_get)
    
    results = list(client.fetch_contacts())
    assert len(results) == 1
    assert results[0]["external_id"] == "k1"
    assert results[0]["full_name"] == "Streak User"

def test_fetch_contacts_pagination(monkeypatch):
    monkeypatch.setenv("STREAK_API_KEY", "test-key")
    
    call_count = 0
    
    def mock_get(url, api_key, params):
        nonlocal call_count
        call_count += 1
        if params["offset"] == 0:
            # Return full page
            return [{"key": f"p1_{i}", "fullName": f"User {i}"} for i in range(100)]
        else:
            # Return partial page to stop
            return [{"key": "p2_1", "fullName": "Last User"}]

    monkeypatch.setattr(client, "_get", mock_get)
    
    results = list(client.fetch_contacts())
    assert len(results) == 101
    assert call_count == 2

def test_fetch_contacts_api_error(monkeypatch):
    monkeypatch.setenv("STREAK_API_KEY", "test-key")
    
    def mock_get(url, api_key, params):
        raise RuntimeError("Streak API request failed: 500 - Internal Server Error URL: http://test/contacts")

    monkeypatch.setattr(client, "_get", mock_get)
    
    with pytest.raises(RuntimeError, match="500 - Internal Server Error"):
        list(client.fetch_contacts())