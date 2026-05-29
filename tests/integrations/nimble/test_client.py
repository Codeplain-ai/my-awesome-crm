import pytest
from unittest.mock import patch
from src.integrations.nimble.client import fetch_contacts

@patch("src.integrations.nimble.client.os.environ.get")
@patch("src.integrations.nimble.client._get")
def test_fetch_contacts_pagination(mock_get, mock_env):
    # Setup Env
    mock_env.side_effect = lambda key, default=None: "fake-token" if key == "NIMBLE_ACCESS_TOKEN" else default

    # Mock responses for 2 pages
    page1 = {
        "resources": [{"id": f"p1-{i}", "fields": {"first name": [{"value": "A"}]}} for i in range(100)],
        "meta": {"page": 1, "pages": 2}
    }
    page2 = {
        "resources": [{"id": "p2-1", "fields": {"first name": [{"value": "B"}]}}],
        "meta": {"page": 2, "pages": 2}
    }
    mock_get.side_effect = [page1, page2]

    results = fetch_contacts()
    
    assert len(results) == 101
    assert mock_get.call_count == 2
    # Verify page increment in params
    assert mock_get.call_args_list[1][0][2]["page"] == 2

@patch("src.integrations.nimble.client.os.environ.get")
def test_fetch_contacts_missing_creds(mock_env):
    mock_env.return_value = None
    with pytest.raises(RuntimeError, match="NIMBLE_ACCESS_TOKEN"):
        fetch_contacts()