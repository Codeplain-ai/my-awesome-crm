import pytest
from src.integrations.streak.mapping import streak_contact_to_incoming

def test_mapping_full_payload():
    payload = {
        "key": "contact_123",
        "fullName": "Alice Smith",
        "emailAddresses": ["ALICE@Example.com", "work@alice.com"],
        "phoneNumbers": ["123-456", "789-000"],
        "title": "Engineer",
        "companyName": "Tech Corp",
        "otherField": "random-value"
    }
    result = streak_contact_to_incoming(payload)
    
    assert result["provider_id"] == "streak"
    assert result["external_id"] == "contact_123"
    assert result["full_name"] == "Alice Smith"
    assert result["primary_email"] == "alice@example.com"
    assert result["phone"] == "123-456"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "Tech Corp"
    assert result["custom_fields"] == {"otherField": "random-value"}

def test_mapping_name_fallback():
    payload = {
        "key": "contact_456",
        "givenName": " Bob ",
        "familyName": "Builder ",
        "emailAddresses": []
    }
    result = streak_contact_to_incoming(payload)
    assert result["full_name"] == "Bob Builder"

def test_mapping_missing_id_raises():
    payload = {"fullName": "No ID"}
    with pytest.raises(ValueError, match="missing the required 'key' field"):
        streak_contact_to_incoming(payload)

def test_mapping_missing_name_raises():
    payload = {"key": "123"}
    with pytest.raises(ValueError, match="missing a valid name"):
        streak_contact_to_incoming(payload)