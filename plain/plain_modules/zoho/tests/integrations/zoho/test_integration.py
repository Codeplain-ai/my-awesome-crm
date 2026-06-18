import pytest
import os
from unittest.mock import patch, MagicMock
from src.integrations.zoho import fetch_contacts

def test_fetch_contacts_missing_creds():
    """Verify RuntimeError is raised if env vars are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="ZOHO_ACCOUNTS_HOST"):
            fetch_contacts()

@patch("src.integrations.zoho.client.httpx.Client")
def test_fetch_contacts_success_flow(mock_client_class):
    """Verify end-to-end success including token refresh and multi-page pagination."""
    # Setup mock env
    mock_env = {
        "ZOHO_ACCOUNTS_HOST": "https://accounts.zoho.com",
        "ZOHO_API_HOST": "https://api.zoho.com",
        "ZOHO_CLIENT_ID": "cid",
        "ZOHO_CLIENT_SECRET": "csec",
        "ZOHO_REFRESH_TOKEN": "rtok"
    }
    
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # 1. Token response
    resp_token = MagicMock()
    resp_token.status_code = 200
    resp_token.json.return_value = {"access_token": "atk_123"}
    
    # 2. Page 1 response (2 records, more_records: true)
    resp_p1 = MagicMock()
    resp_p1.status_code = 200
    resp_p1.json.return_value = {
        "data": [
            {"id": "z1", "Full_Name": "User One"},
            {"id": "z2", "Full_Name": "User Two"}
        ],
        "info": {"more_records": True}
    }
    
    # 3. Page 2 response (1 record, more_records: false)
    resp_p2 = MagicMock()
    resp_p2.status_code = 200
    resp_p2.json.return_value = {
        "data": [{"id": "z3", "Full_Name": "User Three"}],
        "info": {"more_records": False}
    }
    
    mock_client.post.side_effect = [resp_token]
    mock_client.get.side_effect = [resp_p1, resp_p2]
    
    with patch.dict(os.environ, mock_env):
        results = fetch_contacts()
        
    assert len(results) == 3
    assert results[0]["external_id"] == "z1"
    assert results[2]["external_id"] == "z3"
    assert mock_client.get.call_count == 2

@patch("src.integrations.zoho.client.httpx.Client")
def test_fetch_contacts_skip_and_log(mock_client_class):
    """Verify that a mapping failure skips the record but completes the batch."""
    mock_env = {
        "ZOHO_ACCOUNTS_HOST": "h", "ZOHO_API_HOST": "h", "ZOHO_CLIENT_ID": "i", 
        "ZOHO_CLIENT_SECRET": "s", "ZOHO_REFRESH_TOKEN": "r"
    }
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Token
    rt = MagicMock()
    rt.status_code = 200
    rt.json.return_value = {"access_token": "a"}
    
    # Page with one good and one bad record (missing name)
    rp = MagicMock()
    rp.status_code = 200
    rp.json.return_value = {
        "data": [
            {"id": "good", "Full_Name": "Good"},
            {"id": "bad"} # No name -> ValueError in mapper
        ],
        "info": {"more_records": False}
    }
    
    mock_client.post.return_value = rt
    mock_client.get.return_value = rp
    
    with patch.dict(os.environ, mock_env):
        results = fetch_contacts()
        
    assert len(results) == 1
    assert results[0]["external_id"] == "good"

@patch("src.integrations.zoho.client.httpx.Client")
def test_fetch_contacts_204_handling(mock_client_class):
    """Verify 204 No Content results in zero records."""
    mock_env = {
        "ZOHO_ACCOUNTS_HOST": "h", "ZOHO_API_HOST": "h", "ZOHO_CLIENT_ID": "i", 
        "ZOHO_CLIENT_SECRET": "s", "ZOHO_REFRESH_TOKEN": "r"
    }
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    rt = MagicMock()
    rt.status_code = 200
    rt.json.return_value = {"access_token": "a"}
    
    rp = MagicMock()
    rp.status_code = 204 # Empty
    
    mock_client.post.return_value = rt
    mock_client.get.return_value = rp
    
    with patch.dict(os.environ, mock_env):
        results = fetch_contacts()
    
    assert len(results) == 0