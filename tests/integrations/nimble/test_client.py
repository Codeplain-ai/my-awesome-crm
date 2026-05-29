import pytest
from unittest.mock import patch, MagicMock
from src.integrations.nimble.client import fetch_contacts

@patch("src.integrations.nimble.client.os.environ.get")
@patch("src.integrations.nimble.client._get")
def test_fetch_contacts_pagination(mock_get, mock_env):
    # Setup Env
    def env_side_effect(key, default=None):
        if key == "NIMBLE_ACCESS_TOKEN": return "fake-token"
        return default
    mock_env.side_effect = env_side_effect

    # Mock responses for 2 pages
    page1 = {
        "resources": [
            {"id": "1", "fields": {"first name": [{"value": "A"}]}}
        ] * 100,
        "meta": {"page": 1, "pages": 2}
    }
    page2 = {
        "resources": [
            {"id": "101", "fields": {"first name": [{"value": "B"}]}}
        ],
        "meta": {"page": 2, "pages": 2}
    }
    mock_get.side_effect = [page1, page2]

    results = fetch_contacts()
    
    assert len(results) == 101
    assert mock_get.call_count == 2
    # Verify page increment
    assert mock_get.call_args_list[1][0][2]["page"] == 2

@patch("src.integrations.nimble.client.os.environ.get")
def test_fetch_contacts_missing_creds(mock_env):
    mock_env.return_value = None
    with pytest.raises(RuntimeError, match="NIMBLE_ACCESS_TOKEN"):
        list(fetch_contacts())