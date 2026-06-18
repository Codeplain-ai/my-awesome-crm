import pytest
import os
from unittest.mock import patch, MagicMock
from src.integrations.dynamics import fetch_contacts

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("DYNAMICS_ENDPOINT", "https://test.crm.dynamics.com")
    monkeypatch.setenv("DYNAMICS_TENANT_ID", "tenant-123")
    monkeypatch.setenv("DYNAMICS_CLIENT_ID", "client-123")
    monkeypatch.setenv("DYNAMICS_CLIENT_SECRET", "secret-123")

def test_fetch_contacts_missing_env_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("DYNAMICS_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError, match="DYNAMICS_ENDPOINT"):
        list(fetch_contacts())

@patch("httpx.post")
@patch("httpx.Client")
def test_fetch_contacts_multi_page_success(mock_client_class, mock_post, mock_env):
    # 1. Mock Token Response
    mock_token_resp = MagicMock()
    mock_token_resp.json.return_value = {"access_token": "fake-token"}
    mock_token_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_token_resp

    # 2. Mock Data Pages
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    page1 = {
        "value": [
            {"contactid": "id1", "fullname": "User One"},
            {"contactid": "id2", "fullname": "User Two"}
        ],
        "@odata.nextLink": "https://test.crm.dynamics.com/api/data/v9.2/contacts?page=2"
    }
    page2 = {
        "value": [
            {"contactid": "id3", "fullname": "User Three"}
        ]
        # No nextLink
    }
    
    resp1 = MagicMock()
    resp1.json.return_value = page1
    resp2 = MagicMock()
    resp2.json.return_value = page2
    
    mock_client.get.side_effect = [resp1, resp2]

    # Run
    results = list(fetch_contacts())

    # Assertions
    assert len(results) == 3
    assert results[0]["external_id"] == "id1"
    assert results[1]["external_id"] == "id2"
    assert results[2]["external_id"] == "id3"
    assert mock_client.get.call_count == 2

@patch("httpx.post")
@patch("httpx.Client")
def test_fetch_contacts_skip_bad_record(mock_client_class, mock_post, mock_env):
    # Mock Token
    mock_token_resp = MagicMock()
    mock_token_resp.json.return_value = {"access_token": "fake-token"}
    mock_post.return_value = mock_token_resp

    # Mock Data: One good, one missing name (ValueError in map), one good
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    data = {
        "value": [
            {"contactid": "good1", "fullname": "Good One"},
            {"contactid": "bad1"}, # No name -> ValueError
            {"contactid": "good2", "fullname": "Good Two"}
        ]
    }
    
    resp = MagicMock()
    resp.json.return_value = data
    mock_client.get.return_value = resp

    # Run
    results = list(fetch_contacts())

    # Assertions
    assert len(results) == 2
    assert results[0]["external_id"] == "good1"
    assert results[1]["external_id"] == "good2"