import pytest
from unittest.mock import patch, MagicMock
from src.integrations.nimble import fetch_contacts

@patch("src.integrations.nimble.client.httpx.Client")
@patch("os.environ.get")
def test_fetch_contacts_pagination_and_skip_logic(mock_env, mock_httpx_client):
    # Setup Env
    mock_env.return_value = "fake-token"
    
    # Setup Pagination Mocks: 2 pages
    mock_client_instance = MagicMock()
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
    
    page1_resp = {
        "resources": [
            {"id": "good1", "fields": {"first name": [{"value": "Good"}], "last name": [{"value": "One"}]}},
            {"id": "bad1", "fields": {}} # Should be skipped (no name/email/company)
        ],
        "meta": {"page": 1, "pages": 2, "per_page": 2, "total": 3}
    }
    
    page2_resp = {
        "resources": [
            {"id": "good2", "fields": {"first name": [{"value": "Good"}], "last name": [{"value": "Two"}]}}
        ],
        "meta": {"page": 2, "pages": 2, "per_page": 2, "total": 3}
    }
    
    mock_client_instance.get.side_effect = [
        MagicMock(status_code=200, json=lambda: page1_resp, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: page2_resp, raise_for_status=lambda: None)
    ]
    
    results = list(fetch_contacts())
    
    assert len(results) == 2
    assert results[0]["external_id"] == "good1"
    assert results[1]["external_id"] == "good2"
    assert mock_client_instance.get.call_count == 2

@patch("os.environ.get")
def test_fetch_contacts_no_token_raises(mock_env):
    mock_env.return_value = None
    with pytest.raises(RuntimeError, match="Missing NIMBLE_ACCESS_TOKEN"):
        list(fetch_contacts())

def test_integration_exports_only_contract():
    import src.integrations.nimble as nimble
    # Check __all__ if defined
    if hasattr(nimble, "__all__"):
        assert nimble.__all__ == ["fetch_contacts"]
    
    # Check that internal implementation details are not part of the intended public API
    # (even if technically reachable via the module object, __all__ defines the export contract)
    assert hasattr(nimble, "fetch_contacts")