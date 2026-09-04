import pytest
from unittest.mock import MagicMock, patch
from src.integrations.zendesk_sell import fetch

@patch("src.integrations.zendesk_sell.client.httpx.Client")
def test_fetch_with_pagination(MockHttpx, monkeypatch):
    monkeypatch.setenv("ZENDESK_SELL_ACCESS_TOKEN", "valid-token")
    
    # Mock Page 1
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "items": [{"data": {"id": 1, "name": "Contact 1"}}],
        "meta": {"links": {"next_page": "https://api.getbase.com/v2/contacts?page=2"}}
    }
    
    # Mock Page 2 (Final)
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "items": [{"data": {"id": 2, "name": "Contact 2"}}],
        "meta": {"links": {}}
    }
    
    MockHttpx.return_value.__enter__.return_value.get.side_effect = [resp1, resp2]
    
    # Verify get_stored callback functionality (even if not used for filtering in this impl)
    get_stored = MagicMock(return_value=[])
    results = fetch(get_stored)
    
    assert len(results) == 2
    get_stored.assert_not_called() # Zendesk Sell impl doesn't currently use get_stored for delta sync
    assert results[0]["data"]["external_id"] == "1"
    assert results[1]["data"]["external_id"] == "2"

def test_fetch_missing_token(monkeypatch):
    monkeypatch.setenv("ZENDESK_SELL_ACCESS_TOKEN", "")
    with pytest.raises(RuntimeError, match="ZENDESK_SELL_ACCESS_TOKEN"):
        fetch(lambda x: [])

@patch("src.integrations.zendesk_sell.client.httpx.Client")
def test_fetch_api_error(MockHttpx, monkeypatch):
    monkeypatch.setenv("ZENDESK_SELL_ACCESS_TOKEN", "token")
    
    resp = MagicMock()
    resp.status_code = 401
    resp.text = "Unauthorized"
    MockHttpx.return_value.__enter__.return_value.get.return_value = resp
    
    with pytest.raises(RuntimeError, match="401 Unauthorized"):
        fetch(lambda x: [])