import pytest
from src.integrations.zendesk_sell.mapping import map_contact

def test_map_contact_organization():
    payload = {
        "id": 101,
        "is_organization": True,
        "name": "  Global Corp  ",
        "email": "CONTACT@global.com",
        "custom_fields": {"Industry": "Manufacturing"}
    }
    mapped = map_contact(payload)
    assert mapped["external_id"] == "101"
    assert mapped["full_name"] == "Global Corp"
    assert mapped["primary_email"] == "contact@global.com"
    assert mapped["custom_fields"]["Industry"] == "Manufacturing"
    assert mapped["custom_fields"]["is_organization"] is True

def test_map_contact_person():
    payload = {
        "id": 202,
        "is_organization": False,
        "first_name": "Jane",
        "last_name": "Smith",
        "organization_name": "Smith & Co"
    }
    mapped = map_contact(payload)
    assert mapped["full_name"] == "Jane Smith"
    assert mapped["company_name"] == "Smith & Co"
    assert mapped["custom_fields"]["is_organization"] is False

def test_map_contact_name_fallbacks():
    # Fallback to name field
    p1 = {"id": 1, "is_organization": False, "name": "Only Name"}
    assert map_contact(p1)["full_name"] == "Only Name"
    
    # Fallback to email
    p2 = {"id": 2, "is_organization": False, "email": "test@user.com"}
    assert map_contact(p2)["full_name"] == "test@user.com"
    
    # Ultimate fallback
    p3 = {"id": 3, "is_organization": False}
    assert map_contact(p3)["full_name"] == ""

def test_map_contact_provenance():
    payload = {
        "id": 500,
        "created_at": "2026-01-01T12:00:00Z",
        "updated_at": "2026-01-02T12:00:00Z",
        "contact_id": 99
    }
    cf = map_contact(payload)["custom_fields"]
    assert cf["created_at"] == "2026-01-01T12:00:00Z"
    assert cf["updated_at"] == "2026-01-02T12:00:00Z"
    assert cf["contact_id"] == 99