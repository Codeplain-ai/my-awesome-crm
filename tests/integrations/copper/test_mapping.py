import pytest
from src.integrations.copper.mapping import copper_person_to_incoming

def test_mapping_minimal_valid():
    payload = {
        "id": 12345,
        "name": "Jane Doe"
    }
    result = copper_person_to_incoming(payload)
    assert result["provider_id"] == "copper"
    assert result["external_id"] == "12345"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] is None
    assert result["custom_fields"] == {}

def test_mapping_complex():
    payload = {
        "id": 99,
        "name": " John Smith ",
        "emails": [
            {"email": "personal@gmail.com", "category": "other"},
            {"email": "work@corp.com", "category": "work"}
        ],
        "phone_numbers": [
            {"number": "555-0000", "category": "mobile"},
            {"number": "555-1234", "category": "work"}
        ],
        "title": "Engineer",
        "company_name": "ACME",
        "tags": ["vip"],
        "assignee_id": 101
    }
    result = copper_person_to_incoming(payload)
    assert result["full_name"] == "John Smith"
    assert result["primary_email"] == "work@corp.com"
    assert result["phone"] == "555-1234"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "ACME"
    assert result["custom_fields"]["tags"] == ["vip"]
    assert result["custom_fields"]["assignee_id"] == 101
    assert "name" not in result["custom_fields"]

def test_mapping_email_fallback():
    payload = {
        "id": 1,
        "name": "Test",
        "emails": [{"email": "only@test.com", "category": "personal"}]
    }
    result = copper_person_to_incoming(payload)
    assert result["primary_email"] == "only@test.com"

def test_mapping_missing_id():
    with pytest.raises(ValueError, match="missing 'id'"):
        copper_person_to_incoming({"name": "No ID"})

def test_mapping_missing_name():
    with pytest.raises(ValueError, match="missing a non-empty 'name'"):
        copper_person_to_incoming({"id": 1, "name": " "})