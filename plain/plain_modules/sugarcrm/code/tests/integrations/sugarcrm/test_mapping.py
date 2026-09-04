import pytest
from src.integrations.sugarcrm.mapping import map_contact

def test_mapping_full_record():
    """Test mapping with all fields populated."""
    source = {
        "id": "sugar-123",
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe ",
        "email": [
            {"email_address": "secondary@test.com", "primary_address": False},
            {"email_address": "PRIMARY@test.com", "primary_address": True}
        ],
        "title": "Director",
        "account_name": "Acme Corp",
        "date_entered": "2023-01-01T12:00:00Z",
        "date_modified": "2023-01-02T12:00:00Z"
    }
    
    result = map_contact(source)
    
    assert result["provider_id"] == "sugarcrm"
    assert result["external_id"] == "sugar-123"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] == "primary@test.com"
    assert result["job_title"] == "Director"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"]["date_entered"] == "2023-01-01T12:00:00Z"

def test_mapping_name_derivation_from_email():
    """Test that full_name falls back to email when names are missing."""
    source = {
        "id": "sugar-456",
        "email1": " NOBODY@example.com ",
    }
    result = map_contact(source)
    assert result["full_name"] == "nobody@example.com"
    assert result["primary_email"] == "nobody@example.com"

def test_mapping_strips_metadata():
    """Test that _api keys are not in custom_fields."""
    source = {
        "id": "sugar-789",
        "_acl": {"view": "yes"},
        "date_entered": "2023-01-01"
    }
    result = map_contact(source)
    assert "_acl" not in result["custom_fields"]
    assert "date_entered" in result["custom_fields"]

def test_mapping_empty_record():
    """Mapping should never raise for empty records."""
    result = map_contact({"id": "empty"})
    assert result["full_name"] == ""
    assert result["primary_email"] is None
    assert result["custom_fields"] == {}