import pytest
from unittest.mock import patch, MagicMock
from src.integrations.dynamics import fetch

@patch("src.integrations.dynamics.DynamicsClient")
def test_fetch_orchestration_and_pagination(mock_client_class):
    # Mock setup
    mock_client = mock_client_class.return_value
    
    # Simulating two pages
    page1 = [{"contactid": "c1", "fullname": "User One"}]
    page2 = [{"contactid": "c2", "fullname": "User Two"}]
    mock_client.get_contacts.return_value = iter([page1, page2])

    def get_stored(dt): return []
    
    results = fetch(get_stored)
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "c1"
    assert results[1]["data"]["external_id"] == "c2"
    assert results[0]["data_type"] == "contact"

@patch("src.integrations.dynamics.DynamicsClient")
@patch("src.integrations.dynamics.map_contact")
def test_fetch_skip_policy(mock_map, mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.get_contacts.return_value = iter([[{"contactid": "err"}, {"contactid": "ok"}]])
    
    # First call raises ValueError, second succeeds
    mock_map.side_effect = [ValueError("Bad data"), {"external_id": "ok"}]
    
    results = fetch(lambda dt: [])
    
    # Should only contain the 'ok' record
    assert len(results) == 1
    assert results[0]["data"]["external_id"] == "ok"

@patch.dict("os.environ", {}, clear=True)
def test_fetch_missing_env_vars():
    with pytest.raises(RuntimeError) as excinfo:
        fetch(lambda dt: [])
    assert "Missing required environment variables" in str(excinfo.value)
    assert "DYNAMICS_ENDPOINT" in str(excinfo.value)
