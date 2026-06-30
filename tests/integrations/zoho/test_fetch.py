import pytest
from unittest.mock import MagicMock, patch
from src.integrations.zoho import fetch

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("ZOHO_ACCOUNTS_HOST", "https://accounts.zoho.com")
    monkeypatch.setenv("ZOHO_API_HOST", "https://www.zohoapis.com")
    monkeypatch.setenv("ZOHO_CLIENT_ID", "client_id")
    monkeypatch.setenv("ZOHO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ZOHO_REFRESH_TOKEN", "refresh")

def test_fetch_missing_credentials(monkeypatch):
    # Ensure environment is empty
    for var in ["ZOHO_REFRESH_TOKEN", "ZOHO_CLIENT_ID"]:
        monkeypatch.delenv(var, raising=False)
        
    with pytest.raises(RuntimeError) as excinfo:
        fetch(lambda x: [])
    
    assert "ZOHO_ACCOUNTS_HOST" in str(excinfo.value)

@patch("src.integrations.zoho.client.httpx.post")
@patch("src.integrations.zoho.client.httpx.get")
def test_fetch_success_multi_page(mock_get, mock_post, mock_env):
    # Mock Token Response
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "fake_access_token"}
    )
    
    # Mock Data Responses (2 pages)
    page1_data = {
        "data": [{"id": "z1", "Full_Name": "Alice"}],
        "info": {"more_records": True}
    }
    page2_data = {
        "data": [{"id": "z2", "Full_Name": "Bob"}],
        "info": {"more_records": False}
    }
    
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: page1_data),
        MagicMock(status_code=200, json=lambda: page2_data),
    ]
    
    results = fetch(lambda x: [])
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "z1"
    assert results[0]["data_type"] == "contact"
    assert results[1]["data"]["external_id"] == "z2"
    
    # Verify mock calls
    assert mock_post.called
    assert mock_get.call_count == 2

@patch("src.integrations.zoho.client.httpx.post")
@patch("src.integrations.zoho.client.httpx.get")
def test_fetch_204_no_content(mock_get, mock_post, mock_env):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "at"}
    )
    mock_get.return_value = MagicMock(status_code=204)
    
    results = fetch(lambda x: [])
    assert results == []


def test_integration_metadata():
    """Verify the integration exposes the required metadata for discovery."""
    import src.integrations.zoho as zoho
    assert zoho.DATA_TYPE == "contact"
    assert "fetch" in zoho.__all__
    assert "DATA_TYPE" in zoho.__all__
    assert callable(zoho.fetch)