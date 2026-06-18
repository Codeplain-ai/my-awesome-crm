import pytest
from src.integrations.nimble.mapper import map_nimble_contact

def test_map_full_contact():
    raw = {
        "id": "abc-123",
        "record_type": "person",
        "fields": {
            "first name": [{"value": "John"}],
            "last name": [{"value": "Doe"}],
            "email": [{"value": "JOHN.DOE@example.com"}],
            "phone": [{"value": "555-0199"}],
            "title": [{"value": "Engineer"}],
            "company": [{"value": "Acme Corp"}]
        }
    }
    mapped = map_nimble_contact(raw)
    assert mapped["provider_id"] == "nimble"
    assert mapped["external_id"] == "abc-123"
    assert mapped["full_name"] == "John Doe"
    assert mapped["primary_email"] == "john.doe@example.com"
    assert mapped["phone"] == "555-0199"
    assert mapped["job_title"] == "Engineer"
    assert mapped["company_name"] == "Acme Corp"
    assert mapped["custom_fields"]["record_type"] == "person"

def test_name_derivation_fallback_to_email():
    raw = {
        "id": "id-email",
        "fields": {
            "email": [{"value": "ghost@example.com"}]
        }
    }
    mapped = map_nimble_contact(raw)
    assert mapped["full_name"] == "ghost@example.com"

def test_name_derivation_fallback_to_company():
    raw = {
        "id": "id-company",
        "fields": {
            "company": [{"value": "Stark Industries"}]
        }
    }
    mapped = map_nimble_contact(raw)
    assert mapped["full_name"] == "Stark Industries"

def test_invalid_email_mapping_to_none():
    raw = {
        "id": "id-bad-email",
        "fields": {
            "first name": [{"value": "Bad"}],
            "last name": [{"value": "Email"}],
            "email": [{"value": "not-an-email-address"}]
        }
    }
    # Should not raise, but primary_email should be None
    mapped = map_nimble_contact(raw)
    assert mapped["full_name"] == "Bad Email"
    assert mapped["primary_email"] is None

def test_missing_id_raises_value_error():
    raw = {"fields": {"first name": [{"value": "No ID"}]}}
    with pytest.raises(ValueError, match="missing required 'id'"):
        map_nimble_contact(raw)

def test_missing_name_info_raises_value_error():
    raw = {"id": "123", "fields": {}}
    with pytest.raises(ValueError, match="Could not derive full_name"):
        map_nimble_contact(raw)