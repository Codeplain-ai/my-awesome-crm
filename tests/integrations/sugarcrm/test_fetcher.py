import pytest
import os
from unittest.mock import patch, MagicMock
from src.integrations.sugarcrm.fetcher import fetch_contacts

@pytest.fixture
def sugar_env():
    env = {
        "SUGARCRM_ENDPOINT": "https://test.sugar.com",
        "SUGARCRM_CLIENT_ID": "sugar",
        "SUGARCRM_CLIENT_SECRET": "",
        "SUGARCRM_USERNAME": "admin",
        "SUGARCRM_PASSWORD": "password",
    }
    with patch.dict(os.environ, env):
        yield env

def test_fetch_contacts_missing_creds():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="SUGARCRM_ENDPOINT"):
            fetch_contacts()

def test_fetch_contacts_pagination_and_skip(sugar_env):
    # Mock data for two pages
    # Page 1: 1 good, 1 bad (missing ID)
    # Page 2: 1 good, finish (next_offset -1)
    
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "fake-token"}
    
    mock_page1_resp = MagicMock()
    mock_page1_resp.status_code = 200
    mock_page1_resp.json.return_value = {
        "next_offset": 2,
        "records": [
            {"id": "ok-1", "full_name": "Good One"},
            {"full_name": "Missing ID"} # Should raise ValueError in mapping
        ]
    }
    
    mock_page2_resp = MagicMock()
    mock_page2_resp.status_code = 200
    mock_page2_resp.json.return_value = {
        "next_offset": -1,
        "records": [
            {"id": "ok-2", "full_name": "Good Two"}
        ]
    }

    with patch("httpx.Client.post", return_value=mock_token_resp):
        with patch("httpx.Client.get") as mock_get:
            mock_get.side_effect = [mock_page1_resp, mock_page2_resp]
            
            results = fetch_contacts()
            
            assert len(results) == 2
            assert results[0]["external_id"] == "ok-1"
            assert results[1]["external_id"] == "ok-2"
            
            # Verify calls
            assert mock_get.call_count == 2
            # Verify parameters of first call
            args, kwargs = mock_get.call_args_list[0]
            assert kwargs["headers"]["OAuth-Token"] == "fake-token"
            assert kwargs["params"]["max_num"] == 200
            
            # Verify offset in second call
            args, kwargs = mock_get.call_args_list[1]
            assert kwargs["params"]["offset"] == 2

def test_fetch_contacts_token_failure(sugar_env):
    mock_fail = MagicMock()
    mock_fail.status_code = 401
    mock_fail.text = "Unauthorized"
    
    with patch("httpx.Client.post", return_value=mock_fail):
        with pytest.raises(Exception): # httpx.HTTPStatusError or similar
            fetch_contacts()