import pytest
import os
import httpx
from src.integrations.streak import fetch_contacts

def test_fetch_contacts_missing_creds(monkeypatch):
    """Should raise RuntimeError if STREAK_API_KEY is missing."""
    monkeypatch.delenv("STREAK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="STREAK_API_KEY"):
        fetch_contacts()

def test_fetch_contacts_success(monkeypatch):
    """Tests successful retrieval from multiple teams with skip-and-log logic."""
    monkeypatch.setenv("STREAK_API_KEY", "test-key")

    def mock_make_request(url, auth):
        if "users/me/teams" in url:
            return [{"key": "t1"}, {"key": "t2"}]
        if "teams/t1/contacts" in url:
            return [
                {"key": "c1", "fullName": "User One", "emailAddresses": ["one@ex.com"]},
                {"key": "c2", "fullName": "User Two"}
            ]
        if "teams/t2/contacts" in url:
            return [
                {"key": "c3", "fullName": "User Three"},
                {"key": "c4"} # Invalid: no name or email
            ]
        return []

    monkeypatch.setattr("src.integrations.streak._make_request", mock_make_request)
    
    results = fetch_contacts()
    
    # Assertions
    assert len(results) == 3
    assert results[0]["external_id"] == "c1"
    assert results[1]["external_id"] == "c2"
    assert results[2]["external_id"] == "c3"
    # Ensure c4 was skipped without crashing the whole loop

def test_fetch_contacts_api_error(monkeypatch):
    """Should propagate transport/HTTP errors (not skip them)."""
    monkeypatch.setenv("STREAK_API_KEY", "test-key")
    
    def mock_make_request_fail(url, auth):
        # Create a real-looking exception from httpx
        request = httpx.Request("GET", url)
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    monkeypatch.setattr("src.integrations.streak._make_request", mock_make_request_fail)
    
    with pytest.raises(httpx.HTTPStatusError):
        fetch_contacts()