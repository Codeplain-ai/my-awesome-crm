import pytest
from src.integrations.close.mapping import map_close_contact

def test_map_full_contact():
    source = {
        "id": "cont_123",
        "name": " Alice Smith ",
        "title": "Engineer",
        "lead_id": "lead_456",
        "organization_id": "org_789",
        "emails": [{"email": "ALICE@example.com ", "type": "office"}],
        "date_created": "2024-01-01T00:00:00Z",
        "date_updated": "2024-01-02T00:00:00Z"
    }
    result = map_close_contact(source)
    
    assert result["provider_id"] == "close"
    assert result["external_id"] == "cont_123"
    assert result["full_name"] == "Alice Smith"
    assert result["primary_email"] == "alice@example.com"
    assert result["job_title"] == "Engineer"
    assert result["custom_fields"]["lead_id"] == "lead_456"
    assert result["custom_fields"]["date_created"] == "2024-01-01T00:00:00Z"

def test_map_nameless_contact_falls_back_to_email():
    source = {
        "id": "cont_999",
        "name": None,
        "emails": [{"email": "bob@example.com"}]
    }
    result = map_close_contact(source)
    assert result["full_name"] == "bob@example.com"
    assert result["primary_email"] == "bob@example.com"

def test_map_completely_empty_contact():
    source = {"id": "cont_none"}
    result = map_close_contact(source)
    assert result["full_name"] == ""
    assert result["primary_email"] is None
    assert result["job_title"] is None
    assert result["custom_fields"] == {}

def test_custom_fields_excludes_presentation_fields():
    source = {
        "id": "cont_1",
        "display_name": "Should Not Be In Custom",
        "created_by": "user_1",
        "lead_id": "lead_1"
    }
    result = map_close_contact(source)
    assert "display_name" not in result["custom_fields"]
    assert "created_by" not in result["custom_fields"]
    assert result["custom_fields"]["lead_id"] == "lead_1"