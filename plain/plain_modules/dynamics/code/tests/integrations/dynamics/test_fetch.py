import pytest
import os
from unittest.mock import MagicMock, patch
from src.integrations.dynamics import fetch

@patch("src.integrations.dynamics.DynamicsClient")
@patch.dict(os.environ, {
    "DYNAMICS_CLIENT_ID": "test-cid",
    "DYNAMICS_CLIENT_SECRET": "test-sec",
    "DYNAMICS_TENANT_ID": "test-tid",
    "DYNAMICS_ENDPOINT": "https://test.crm.dynamics.com"
})
def test_fetch_multi_page_pagination(mock_client_class):
    # Setup mock client to return two pages
    mock_client = mock_client_class.return_value
    mock_client.list_contacts.return_value = iter([
        [{"contactid": "1", "fullname": "User One"}],
        [{"contactid": "2", "fullname": "User Two"}]
    ])
    
    # Mock get_stored callback (not used in this logic but required by contract)
    get_stored = MagicMock(return_value=[])
    
    results = fetch(get_stored)
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "1"
    assert results[1]["data"]["external_id"] == "2"
    assert all(r["data_type"] == "contact" for r in results)

@patch.dict(os.environ, {}, clear=True)
def test_fetch_missing_env_vars_raises_runtime_error():
    with pytest.raises(RuntimeError) as exc:
        fetch(lambda x: [])
    assert "Missing required environment variables" in str(exc.value)
    assert "DYNAMICS_ENDPOINT" in str(exc.value)

@patch("src.integrations.dynamics.DynamicsClient")
@patch.dict(os.environ, {
    "DYNAMICS_CLIENT_ID": "cid",
    "DYNAMICS_CLIENT_SECRET": "sec",
    "DYNAMICS_TENANT_ID": "tid",
    "DYNAMICS_ENDPOINT": "https://test.crm.dynamics.com"
})
def test_fetch_skip_and_log_policy(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.list_contacts.return_value = iter([
        [{"contactid": "good", "fullname": "Good"}, {"contactid": "bad", "fullname": "Bad"}]
    ])
    
    # Inject a side effect into the mapping call
    with patch("src.integrations.dynamics.map_contact_record") as mock_map:
        def side_effect(rec):
            if rec["contactid"] == "bad":
                raise ValueError("Simulated mapping error")
            return {"external_id": rec["contactid"]}
        
        mock_map.side_effect = side_effect
        
        results = fetch(lambda x: [])
        
        # Batch policy: 1 record mapped, 1 record skipped
        assert len(results) == 1
        assert results[0]["data"]["external_id"] == "good"