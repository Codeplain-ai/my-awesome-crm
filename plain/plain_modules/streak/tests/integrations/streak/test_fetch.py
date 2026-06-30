import pytest
import os
import httpx
from unittest.mock import patch, MagicMock
from src.integrations.streak import fetch

@patch("httpx.Client")
def test_fetch_success(mock_client_class):
    # Setup mock client
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Mock STREAK_API_KEY
    with patch.dict(os.environ, {"STREAK_API_KEY": "test-key"}):
        
        # 1. Mock Teams Response
        mock_teams_resp = MagicMock()
        mock_teams_resp.json.return_value = [{"key": "team_a"}, {"key": "team_b"}]
        mock_teams_resp.raise_for_status.return_value = None
        
        # 2. Mock Contacts Responses
        mock_contacts_a_resp = MagicMock()
        mock_contacts_a_resp.json.return_value = [
            {"key": "c1", "fullName": "Team A Contact"}
        ]
        mock_contacts_a_resp.raise_for_status.return_value = None
        
        mock_contacts_b_resp = MagicMock()
        mock_contacts_b_resp.json.return_value = [
            {"key": "c2", "fullName": "Team B Contact"}
        ]
        mock_contacts_b_resp.raise_for_status.return_value = None

        # Side effect to handle sequential calls to client.get
        mock_client.get.side_effect = [
            mock_teams_resp,
            mock_contacts_a_resp,
            mock_contacts_b_resp
        ]
        
        get_stored = MagicMock(return_value=[])
        results = fetch(get_stored)
        
        assert len(results) == 2
        assert results[0]["data"]["full_name"] == "Team A Contact"
        assert results[1]["data"]["full_name"] == "Team B Contact"
        assert results[0]["data_type"] == "contact"

def test_fetch_missing_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError) as excinfo:
            fetch(lambda t: [])
        assert "Missing STREAK_API_KEY" in str(excinfo.value)

@patch("httpx.Client")
def test_fetch_http_error(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    with patch.dict(os.environ, {"STREAK_API_KEY": "test-key"}):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        # Simulate raise_for_status raising
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_resp
        )
        mock_client.get.return_value = mock_resp

        with pytest.raises(RuntimeError) as excinfo:
            fetch(lambda t: [])
        
        # Verify extensive error information
        assert "Streak API HTTP error" in str(excinfo.value)
        assert "401" in str(excinfo.value)
        assert "Unauthorized" in str(excinfo.value)


def test_integration_exports():
    """Verify the integration package exports the required interface."""
    import src.integrations.streak as streak
    assert hasattr(streak, "fetch")
    assert callable(streak.fetch)
    assert hasattr(streak, "DATA_TYPE")
    assert streak.DATA_TYPE == "contact"
    assert "fetch" in streak.__all__
    assert "DATA_TYPE" in streak.__all__