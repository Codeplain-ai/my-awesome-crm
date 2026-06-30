import pytest
from unittest.mock import patch, MagicMock
from src.integrations.zendesk_sell import fetch

@patch("src.integrations.zendesk_sell.client.ZendeskSellClient.list_all_contacts")
@patch.dict("os.environ", {"ZENDESK_SELL_ACCESS_TOKEN": "fake_token"})
def test_fetch_success(mock_list):
    # Setup mock data for two items
    mock_list.return_value = iter([
        {"data": {"id": 1, "name": "Org 1", "is_organization": True}},
        {"data": {"id": 2, "first_name": "John", "last_name": "Smith"}}
    ])
    
    get_stored = MagicMock(return_value=[])
    results = fetch(get_stored)
    
    assert len(results) == 2
    assert all(r["data_type"] == "contact" for r in results)
    assert results[0]["data"]["external_id"] == "1"
    assert results[1]["data"]["full_name"] == "John Smith"

@patch.dict("os.environ", {}, clear=True)
def test_fetch_missing_credentials():
    get_stored = MagicMock()
    with pytest.raises(RuntimeError) as excinfo:
        fetch(get_stored)
    assert "ZENDESK_SELL_ACCESS_TOKEN" in str(excinfo.value)

@patch("httpx.Client.get")
@patch.dict("os.environ", {"ZENDESK_SELL_ACCESS_TOKEN": "fake_token"})
def test_fetch_pagination(mock_get):
    # Mock first page response
    page1 = {
        "items": [{"data": {"id": 101, "name": "P1"}}],
        "meta": {"links": {"next_page": "https://api.getbase.com/v2/contacts?page=2"}}
    }
    # Mock second page response
    page2 = {
        "items": [{"data": {"id": 102, "name": "P2"}}],
        "meta": {"links": {}} # No next_page
    }
    
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: page1, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: page2, raise_for_status=lambda: None),
    ]
    
    from src.integrations.zendesk_sell import fetch
    results = fetch(lambda t: [])
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "101"
    assert results[1]["data"]["external_id"] == "102"