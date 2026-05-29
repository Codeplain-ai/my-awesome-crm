import pytest
from unittest.mock import patch
from src.integrations.zendesk_sell.client import fetch_contacts

def test_fetch_contacts_missing_token():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="ZENDESK_SELL_ACCESS_TOKEN"):
            list(fetch_contacts())

def test_fetch_contacts_pagination_and_filtering(monkeypatch):
    # Mock data for 2 pages
    page1 = {
        "items": [
            {"data": {"id": 1, "name": "Person 1", "is_organization": False}},
            {"data": {"id": 2, "name": "Org 1", "is_organization": True}}
        ]
    }
    page2 = {
        "items": [
            {"data": {"id": 3, "name": "Person 2", "is_organization": False}}
        ]
    }
    page3 = {"items": []}

    pages = [page1, page2, page3]
    call_count = 0

    def mock_get_page(base_url, token, page):
        nonlocal call_count
        p = pages[call_count]
        call_count += 1
        return p

    monkeypatch.setenv("ZENDESK_SELL_ACCESS_TOKEN", "fake-token")
    monkeypatch.setattr("src.integrations.zendesk_sell.client._get_contacts_page", mock_get_page)

    results = list(fetch_contacts())
    
    assert len(results) == 2
    assert results[0]["external_id"] == "1"
    assert results[1]["external_id"] == "3"
    assert call_count == 3