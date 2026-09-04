import pytest
from src.integrations.nimble.mapping import map_contact

def test_mapping_full_name_derivation_from_parts():
    source = {
        "id": "123",
        "fields": {
            "first name": [{"value": " John "}],
            "last name": [{"value": "Doe"}]
        }
    }
    result = map_contact(source)
    assert result["full_name"] == "John Doe"

def test_mapping_full_name_fallback_to_email():
    source = {
        "id": "123",
        "fields": {
            "email": [{"value": " work@example.com "}]
        }
    }
    result = map_contact(source)
    assert result["full_name"] == "work@example.com"
    assert result["primary_email"] == "work@example.com"

def test_mapping_full_name_fallback_to_company():
    source = {
        "id": "123",
        "fields": {
            "company": [{"value": "Acme Corp"}]
        }
    }
    result = map_contact(source)
    assert result["full_name"] == "Acme Corp"
    assert result["company_name"] == "Acme Corp"

def test_mapping_custom_fields_preserves_record_type():
    source = {
        "id": "123",
        "record_type": "person",
        "fields": {"title": [{"value": "CEO"}]}
    }
    result = map_contact(source)
    assert result["custom_fields"] == {"record_type": "person"}
    assert result["job_title"] == "CEO"

def test_mapping_empty_record_returns_defaults():
    # Requirement: The mapping function does not raise for record content.
    source = {"id": "456", "fields": {}}
    result = map_contact(source)
    assert result["full_name"] == ""
    assert result["external_id"] == "456"
    assert result["primary_email"] is None