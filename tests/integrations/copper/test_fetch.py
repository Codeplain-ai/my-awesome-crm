import pytest
from unittest.mock import MagicMock, patch
import httpx
from src.integrations.copper import fetch_contacts

def test_fetch_contacts_pagination(monkeypatch):
    """Tests multi-page pagination and data aggregation."""
    monkeypatch.setenv("COPPER_API_KEY", "test-key")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")

    # Mock first page (full)
    page1_data = [{"id": i, "name": f"User {i}"} for i in range(1, 201)]
    # Mock second page (partial)
    page2_data = [{"id": 201, "name": "User 201"}]

    mock_resp1 = MagicMock(spec=httpx.Response)
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = page1_data

    mock_resp2 = MagicMock(spec=httpx.Response)
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = page2_data

    with patch("httpx.Client.post") as mock_post:
        mock_post.side_effect = [mock_resp1, mock_resp2]
        
        results = fetch_contacts()
        assert len(results) == 201
        assert results[0]["external_id"] == "1"
        assert results[200]["external_id"] == "201"
        assert mock_post.call_count == 2

def test_fetch_contacts_skip_and_log(monkeypatch, caplog):
    """Tests that a page with one bad record yields good ones and logs a warning."""
    monkeypatch.setenv("COPPER_API_KEY", "test-key")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")

    # One good record, one missing name (ValueError)
    records = [
        {"id": 100, "name": "Good User"},
        {"id": 101, "name": ""} 
    ]

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = records

    with patch("httpx.Client.post", return_value=mock_resp):
        results = fetch_contacts()
    
    assert len(results) == 1
    assert results[0]["external_id"] == "100"
    assert "Skipping malformed Copper record 101" in caplog.text

def test_fetch_contacts_missing_creds(monkeypatch):
    """Tests that missing credentials raise RuntimeError."""
    monkeypatch.delenv("COPPER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="COPPER_API_KEY"):
        fetch_contacts()

def test_fetch_contacts_auth_failure(monkeypatch):
    """Tests that 401 Unauthorized propagates."""
    monkeypatch.setenv("COPPER_API_KEY", "wrong")
    monkeypatch.setenv("COPPER_USER_EMAIL", "test@example.com")

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401
    # raise_for_status is what fetch_contacts calls
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=mock_resp
    )

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError):
            fetch_contacts()