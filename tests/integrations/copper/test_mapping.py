import pytest
import logging
from src.integrations.copper.mapping import map_copper_contact

def test_map_copper_contact_success_full():
    """Tests mapping with all fields present and valid."""
    raw = {
        "id": 12345,
        "name": "  Jane Doe  ",
        "emails": [{"email": " JANE@example.com ", "category": "work"}],
        "phone_numbers": [{"number": "555-0101", "category": "mobile"}],
        "title": "Engineer",
        "company_name": "ACME Corp",
        "date_created": 1600000000,
        "date_modified": 1600000001
    }
    
    result = map_copper_contact(raw)
    
    assert result["provider_id"] == "copper"
    assert result["external_id"] == "12345"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] == "jane@example.com"
    assert result["phone"] == "555-0101"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "ACME Corp"
    assert result["custom_fields"]["date_created"] == 1600000000

def test_map_copper_contact_name_derivation():
    """Tests fallback from 'name' to first/last name."""
    raw = {
        "id": 12346,
        "first_name": "John",
        "last_name": "Smith",
        "name": None
    }
    result = map_copper_contact(raw)
    assert result["full_name"] == "John Smith"

def test_map_copper_contact_invalid_email_logged(caplog):
    """Tests that invalid email results in None but doesn't crash."""
    raw = {
        "id": 12347,
        "name": "Bad Email User",
        "emails": [{"email": "not-an-email", "category": "work"}]
    }
    
    with caplog.at_level(logging.WARNING):
        result = map_copper_contact(raw)
    
    assert result["primary_email"] is None
    assert "invalid email format" in caplog.text
    assert "12347" in caplog.text

def test_map_copper_contact_missing_id():
    """Tests that missing ID raises ValueError."""
    raw = {"name": "No ID User"}
    with pytest.raises(ValueError, match="missing required field: id"):
        map_copper_contact(raw)

def test_map_copper_contact_underivable_name():
    """Tests that missing name fields raises ValueError."""
    raw = {"id": 999, "name": "", "first_name": None, "last_name": "  "}
    with pytest.raises(ValueError, match="no derivable full_name"):
        map_copper_contact(raw)

def test_map_copper_contact_custom_fields_isolation():
    """Ensures business keys aren't leaked into custom_fields."""
    raw = {
        "id": 101,
        "name": "Check Customs",
        "title": "Boss",
        "date_created": 12345
    }
    result = map_copper_contact(raw)
    # job_title is a top-level field, should not be in custom_fields
    assert "title" not in result["custom_fields"]
    assert "date_created" in result["custom_fields"]