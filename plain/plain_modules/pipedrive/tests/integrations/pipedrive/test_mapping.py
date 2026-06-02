import pytest
from src.integrations.pipedrive.mapping import pipedrive_person_to_incoming

def test_mapping_full_payload():
    person = {
        "id": 123,
        "name": "John Doe",
        "email": [
            {"value": "work@example.com", "primary": False},
            {"value": "john@doe.com", "primary": True}
        ],
        "phone": [{"value": "555-1234", "primary": True}],
        "job_title": "Engineer",
        "org_name": "Acme Corp",
        "custom_prop": "extra-value"
    }
    
    result = pipedrive_person_to_incoming(person)
    
    assert result["provider_id"] == "pipedrive"
    assert result["external_id"] == "123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john@doe.com"
    assert result["phone"] == "555-1234"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {"custom_prop": "extra-value"}

def test_mapping_name_fallback():
    person = {
        "id": 456,
        "first_name": "Jane",
        "last_name": "Smith",
        "email": [{"value": "jane@smith.com"}]
    }
    result = pipedrive_person_to_incoming(person)
    assert result["full_name"] == "Jane Smith"

def test_mapping_missing_id_raises():
    with pytest.raises(ValueError, match="missing required field: id"):
        pipedrive_person_to_incoming({"name": "No ID"})

def test_mapping_no_name_raises():
    with pytest.raises(ValueError, match="has no valid name"):
        pipedrive_person_to_incoming({"id": 1})