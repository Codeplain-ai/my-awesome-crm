import pytest
from src.integrations.nimble.mapping import nimble_contact_to_incoming

def test_mapping_full_contact():
    payload = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "fields": {
            "first name": [{"value": "John", "modifier": ""}],
            "last name": [{"value": "Doe", "modifier": ""}],
            "email": [{"value": " JOHN.doe@example.com ", "modifier": "work"}],
            "phone": [{"value": "555-1234", "modifier": "mobile"}],
            "title": [{"value": "Engineer", "modifier": ""}],
            "company name": [{"value": "Nimble Corp", "modifier": ""}],
            "skype id": [{"value": "jdoe_skype", "modifier": ""}]
        },
        "tags": ["vip"],
        "owner_id": "123"
    }
    
    result = nimble_contact_to_incoming(payload)
    
    assert result["provider_id"] == "nimble"
    assert result["external_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john.doe@example.com"
    assert result["phone"] == "555-1234"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "Nimble Corp"
    assert result["custom_fields"]["tags"] == ["vip"]
    assert result["custom_fields"]["fields"]["skype id"] == [{"value": "jdoe_skype", "modifier": ""}]

def test_mapping_missing_optional_fields():
    payload = {
        "id": "abc-123",
        "fields": {
            "first name": [{"value": "OnlyName", "modifier": ""}]
        }
    }
    result = nimble_contact_to_incoming(payload)
    assert result["full_name"] == "OnlyName"
    assert result["primary_email"] is None
    assert result["company_name"] is None

def test_mapping_missing_id():
    payload = {"fields": {"first name": [{"value": "Fail"}]}}
    with pytest.raises(ValueError, match="missing required 'id'"):
        nimble_contact_to_incoming(payload)

def test_mapping_missing_name():
    payload = {"id": "123", "fields": {}}
    with pytest.raises(ValueError, match="no valid name"):
        nimble_contact_to_incoming(payload)