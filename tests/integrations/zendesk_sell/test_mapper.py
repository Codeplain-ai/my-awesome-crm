import pytest
from src.integrations.zendesk_sell.mapper import map_zendesk_contact

def test_map_person_success():
    payload = {
        "id": 12345,
        "is_organization": False,
        "first_name": " Jane ",
        "last_name": "Doe",
        "email": "JANE@example.com",
        "phone": "555-0100",
        "title": "Engineer",
        "organization_name": "ACME Corp",
        "custom_fields": {"LegacyID": "XYZ"},
        "created_at": "2023-01-01T00:00:00Z"
    }
    result = map_zendesk_contact(payload)
    
    assert result["provider_id"] == "zendesk_sell"
    assert result["external_id"] == "12345"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] == "jane@example.com"
    assert result["phone"] == "555-0100"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "ACME Corp"
    assert result["custom_fields"]["LegacyID"] == "XYZ"
    assert result["custom_fields"]["created_at"] == "2023-01-01T00:00:00Z"

def test_map_organization_success():
    payload = {
        "id": 999,
        "is_organization": True,
        "name": "Global Industries",
        "email": "info@global.com"
    }
    result = map_zendesk_contact(payload)
    assert result["full_name"] == "Global Industries"
    assert result["external_id"] == "999"

def test_full_name_fallback_to_email():
    payload = {
        "id": 55,
        "email": "fallback@example.com"
    }
    result = map_zendesk_contact(payload)
    assert result["full_name"] == "fallback@example.com"

def test_invalid_email_handling(caplog):
    payload = {
        "id": 101,
        "first_name": "Bad",
        "last_name": "Email",
        "email": "not-an-email"
    }
    result = map_zendesk_contact(payload)
    # Contact still maps
    assert result["full_name"] == "Bad Email"
    # Email is None
    assert result["primary_email"] is None
    # Warning is logged
    assert "101" in caplog.text
    assert "not-an-email" in caplog.text

def test_missing_id_raises_value_error():
    payload = {"first_name": "No", "last_name": "ID"}
    with pytest.raises(ValueError, match="missing required 'id'"):
        map_zendesk_contact(payload)

def test_underivable_name_raises_value_error():
    payload = {"id": 102} # No name, no email, no first/last
    with pytest.raises(ValueError, match="no derivable full_name"):
        map_zendesk_contact(payload)

def test_phone_priority():
    payload = {
        "id": 1, 
        "name": "Test", 
        "phone": "111", 
        "mobile": "222"
    }
    result = map_zendesk_contact(payload)
    assert result["phone"] == "111"
    
    payload_mobile_only = {
        "id": 2, 
        "name": "Test", 
        "mobile": "222"
    }
    result2 = map_zendesk_contact(payload_mobile_only)
    assert result2["phone"] == "222"

def test_fetch_contacts_pagination_and_skip(monkeypatch):
    """
    Tests multi-page fetching, credential checking, and skip-and-log policy.
    """
    monkeypatch.setenv("ZENDESK_SELL_ACCESS_TOKEN", "fake-token")
    
    page1 = {
        "items": [
            {"data": {"id": 1, "name": "Valid One"}},
            {"data": {"id": 2}} # Should trigger ValueError (no name/email)
        ],
        "meta": {"links": {"next_page": "https://api.getbase.com/v2/contacts?page=2"}}
    }
    page2 = {
        "items": [
            {"data": {"id": 3, "name": "Valid Two"}}
        ],
        "meta": {"links": {}}
    }

    call_count = 0

    class MockResponse:
        def __init__(self, json_data):
            self._json = json_data
            self.status_code = 200
        def json(self): return self._json
        def raise_for_status(self): pass

    def mock_get(self, url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "page=2" in str(url):
            return MockResponse(page2)
        return MockResponse(page1)

    import httpx
    monkeypatch.setattr(httpx.Client, "get", mock_get)

    from src.integrations.zendesk_sell import fetch_contacts
    
    results = fetch_contacts()
    
    assert len(results) == 2
    assert results[0]["external_id"] == "1"
    assert results[1]["external_id"] == "3"
    assert call_count == 2

def test_fetch_contacts_missing_creds(monkeypatch):
    monkeypatch.delenv("ZENDESK_SELL_ACCESS_TOKEN", raising=False)
    from src.integrations.zendesk_sell import fetch_contacts
    with pytest.raises(RuntimeError, match="ZENDESK_SELL_ACCESS_TOKEN"):
        fetch_contacts()

def test_integration_exports():
    """
    Verify that the package only exports the required fetch_contacts callable.
    """
    import src.integrations.zendesk_sell as integration
    # Check __all__ if defined
    if hasattr(integration, "__all__"):
        assert integration.__all__ == ["fetch_contacts"]
    
    # Check actual callable
    assert hasattr(integration, "fetch_contacts")
    assert callable(integration.fetch_contacts)