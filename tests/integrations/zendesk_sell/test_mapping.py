import pytest
from src.integrations.zendesk_sell.mapping import zendesk_sell_contact_to_incoming

def test_mapping_full_name_from_name():
    payload = {
        "id": 123,
        "name": "John Doe",
        "email": "JOHN@example.com",
        "phone": "555-1234",
        "is_organization": False
    }
    result = zendesk_sell_contact_to_incoming(payload)
    assert result["full_name"] == "John Doe"
    assert result["external_id"] == "123"
    assert result["primary_email"] == "john@example.com"
    assert result["custom_fields"]["is_organization"] is False

def test_mapping_full_name_fallback():
    payload = {
        "id": 456,
        "first_name": "  Jane ",
        "last_name": "Smith  ",
        "title": "Engineer"
    }
    result = zendesk_sell_contact_to_incoming(payload)
    assert result["full_name"] == "Jane Smith"
    assert result["job_title"] == "Engineer"

def test_mapping_missing_id_raises():
    payload = {"name": "No ID"}
    with pytest.raises(ValueError, match="missing 'id'"):
        zendesk_sell_contact_to_incoming(payload)

def test_mapping_missing_name_raises():
    payload = {"id": 999}
    with pytest.raises(ValueError, match="missing a valid name"):
        zendesk_sell_contact_to_incoming(payload)

def test_mapping_custom_fields_preservation():
    payload = {
        "id": 1,
        "name": "Test",
        "custom_fields": {"coffee_preference": "latte"},
        "tags": ["vip", "lead"]
    }
    result = zendesk_sell_contact_to_incoming(payload)
    assert result["custom_fields"]["custom_fields"] == {"coffee_preference": "latte"}
    assert "vip" in result["custom_fields"]["tags"]