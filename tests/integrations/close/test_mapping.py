import pytest
from src.integrations.close.mapping import map_close_contact

def test_mapping_full_record():
    raw = {
        "id": "cont_123",
        "name": "Jane Doe",
        "title": "Engineer",
        "lead_id": "lead_456",
        "organization_id": "org_789",
        "emails": [{"email": "jane@example.com", "type": "office"}],
        "phones": [{"phone": "+1555123456", "type": "mobile"}],
        "date_created": "2024-01-01T00:00:00Z",
        "date_updated": "2024-01-02T00:00:00Z"
    }
    result = map_close_contact(raw)
    
    assert result["external_id"] == "cont_123"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] == "jane@example.com"
    assert result["phone"] == "+1555123456"
    assert result["job_title"] == "Engineer"
    assert result["custom_fields"]["lead_id"] == "lead_456"

def test_mapping_name_fallback_to_email():
    raw = {
        "id": "cont_no_name",
        "name": None,
        "emails": [{"email": "fallback@example.com"}]
    }
    result = map_close_contact(raw)
    assert result["full_name"] == "fallback@example.com"

def test_mapping_invalid_email_becomes_none():
    # Validates that primary_email is None but record is NOT skipped
    raw = {
        "id": "cont_bad_email",
        "name": "Bad Email Guy",
        "emails": [{"email": "not-an-email"}]
    }
    result = map_close_contact(raw)
    assert result["full_name"] == "Bad Email Guy"
    assert result["primary_email"] is None

def test_mapping_missing_id_raises_value_error():
    raw = {"name": "No ID"}
    with pytest.raises(ValueError, match="missing 'id'"):
        map_close_contact(raw)

def test_mapping_underivable_name_raises_value_error():
    raw = {"id": "cont_999", "name": "", "emails": []}
    with pytest.raises(ValueError, match="no derivable full_name"):
        map_close_contact(raw)