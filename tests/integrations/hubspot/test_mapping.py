import pytest
from src.integrations.hubspot.mapping import map_contact

def test_map_contact_full():
    payload = {
        "id": "123",
        "properties": {
            "firstname": " Jane ",
            "lastname": "Doe",
            "email": "JANE@Example.com ",
            "jobtitle": "Engineer",
            "company": "ACME"
        }
    }
    result = map_contact(payload)
    assert result["provider_id"] == "hubspot"
    assert result["external_id"] == "123"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] == "jane@example.com"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "ACME"
    assert result["custom_fields"] == {}

def test_map_contact_minimal():
    payload = {
        "id": "456",
        "properties": {}
    }
    result = map_contact(payload)
    assert result["external_id"] == "456"
    assert result["full_name"] == ""
    assert result["primary_email"] is None
    assert result["job_title"] is None
    assert result["company_name"] is None

def test_map_contact_email_whitespace():
    payload = {
        "id": "789",
        "properties": {
            "email": "  UPPER@example.com  "
        }
    }
    result = map_contact(payload)
    assert result["primary_email"] == "upper@example.com"

def test_map_contact_missing_properties():
    payload = {"id": "789"}
    result = map_contact(payload)
    assert result["external_id"] == "789"
    assert result["full_name"] == ""
