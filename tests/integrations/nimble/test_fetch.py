import pytest
from unittest.mock import patch, MagicMock
from src.integrations.nimble import fetch

@patch("src.integrations.nimble.client.NimbleClient.list_contacts_page")
@patch.dict("os.environ", {"NIMBLE_ACCESS_TOKEN": "fake_token"})
def test_fetch_multi_page(mock_get_page):
    # Mock Page 1
    mock_get_page.side_effect = [
        {
            "resources": [{"id": "1", "fields": {"first name": [{"value": "P1"}]}}],
            "meta": {"page": 1, "pages": 2, "per_page": 1, "total": 2}
        },
        # Mock Page 2
        {
            "resources": [{"id": "2", "fields": {"first name": [{"value": "P2"}]}}],
            "meta": {"page": 2, "pages": 2, "per_page": 1, "total": 2}
        }
    ]

    results = fetch(get_stored=lambda t: [])
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "1"
    assert results[0]["data"]["full_name"] == "P1"
    assert results[1]["data"]["external_id"] == "2"
    assert results[1]["data"]["full_name"] == "P2"
    assert results[0]["data_type"] == "contact"
    
    assert mock_get_page.call_count == 2

@patch("src.integrations.nimble.client.NimbleClient.list_contacts_page")
@patch.dict("os.environ", {"NIMBLE_ACCESS_TOKEN": "fake_token"})
def test_fetch_auth_failure(mock_get_page):
    mock_get_page.side_effect = RuntimeError("Nimble API authentication failed (401)")
    
    with pytest.raises(RuntimeError, match="Nimble API authentication failed \(401\)"):
        fetch(get_stored=lambda t: [])

@patch.dict("os.environ", {}, clear=True)
def test_fetch_missing_credentials():
    with pytest.raises(RuntimeError, match="NIMBLE_ACCESS_TOKEN"):
        fetch(get_stored=lambda t: [])