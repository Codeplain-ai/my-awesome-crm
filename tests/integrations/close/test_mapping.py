import pytest
from src.integrations.close.mapping import close_contact_to_incoming

def test_mapping_basic_fields():
    raw = {
        "id": "cont_123",
        "name": "Jane Doe",
        "title": "Engineer",
        "emails": [{"email": "jane@example.com", "type": "office"}],
        "phones": [{"phone": "+123456", "type": "office"}],
        "lead_id": "lead_999"
    }
    result = close_contact_to_incoming(raw)
    
    assert result["provider_id"] == "close"
    assert result["external_id"] == "cont_123"
    assert result["full_name"] == "Jane Doe"
    assert result["job_title"] == "Engineer"
    assert result["primary_email"] == "jane@example.com"
    assert result["phone"] == "+123456"
    assert result["custom_fields"]["lead_id"] == "lead_999"

def test_mapping_email_priority():
    raw = {
        "id": "cont_456",
        "name": "Bob",
        "emails": [
            {"email": "personal@gmail.com", "type": "home"},
            {"email": "work@corp.com", "type": "office"}
        ]
    }
    result = close_contact_to_incoming(raw)
    assert result["primary_email"] == "work@corp.com"

def test_mapping_missing_name_raises():
    raw = {"id": "cont_789", "name": ""}
    with pytest.raises(ValueError, match="missing a non-empty 'name'"):
        close_contact_to_incoming(raw)

def test_mapping_custom_fields_isolation():
    raw = {
        "id": "c1",
        "name": "N",
        "custom.cf_favorite_color": "blue"
    }
    result = close_contact_to_incoming(raw)
    assert result["custom_fields"]["custom.cf_favorite_color"] == "blue"
    assert "name" not in result["custom_fields"]