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
    
    def mock_get(url, api_key):
        assert api_key == "test-key"
        assert "/contacts" in url
        return mock_data

    monkeypatch.setattr(client, "_get", mock_get)
    
    results = list(client.fetch_contacts())
    assert len(results) == 1
    assert results[0]["external_id"] == "k1"
    assert results[0]["full_name"] == "Streak User"