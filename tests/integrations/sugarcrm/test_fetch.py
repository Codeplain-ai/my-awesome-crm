from unittest.mock import MagicMock, patch
import pytest
from src.integrations.sugarcrm import fetch

@patch("src.integrations.sugarcrm.SugarCrmClient")
def test_fetch_orchestration_and_pagination(MockClientClass):
    # Setup mock client
    mock_client = MockClientClass.return_value
    mock_client._get_token.return_value = "fake-token"
    
    # Page 1 returns one record and a next_offset
    # Page 2 returns one record and -1
    mock_client.fetch_contacts_page.side_effect = [
        ([{"id": "c1", "full_name": "Contact One"}], 200),
        ([{"id": "c2", "full_name": "Contact Two"}], -1)
    ]
    
    def dummy_get_stored(dt): return []
    
    results = fetch(dummy_get_stored)
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "c1"
    assert results[1]["data"]["external_id"] == "c2"
    assert results[0]["data_type"] == "contact"
    
    # Verify client calls
    assert mock_client.fetch_contacts_page.call_count == 2
    mock_client.fetch_contacts_page.assert_any_call("fake-token", 0)
    mock_client.fetch_contacts_page.assert_any_call("fake-token", 200)

@patch("src.integrations.sugarcrm.SugarCrmClient")
def test_fetch_auth_failure_propagates(MockClientClass):
    mock_client = MockClientClass.return_value
    mock_client._get_token.side_effect = RuntimeError("Auth failed")
    
    with pytest.raises(RuntimeError, match="Auth failed"):
        fetch(lambda dt: [])

@patch.dict("os.environ", {}, clear=True)
def test_fetch_missing_credentials_raises_runtime_error():
    # Clear environment to trigger validation error
    with pytest.raises(RuntimeError, match="Missing required environment variable: SUGARCRM_ENDPOINT"):
        fetch(lambda dt: [])


def test_integration_exports():
    """Verify the integration exports the expected host contract."""
    import src.integrations.sugarcrm as sugarcrm
    assert hasattr(sugarcrm, "fetch")
    assert callable(sugarcrm.fetch)
    assert hasattr(sugarcrm, "DATA_TYPE")
    assert sugarcrm.DATA_TYPE == "contact"
    # Verify __all__ matches the host's expectations
    assert "fetch" in sugarcrm.__all__
    assert "DATA_TYPE" in sugarcrm.__all__