import pytest
from src.integrations.sugarcrm.mapping import map_contact

def test_map_contact_success_standard():
    raw = {
        "id": "sugar-123",
        "full_name": " John Doe ",
        "email": [
            {"email_address": "PRIMARY@example.com", "primary_address": True},
            {"email_address": "other@example.com", "primary_address": False}
        ],
        "phone_work": "555-0101",
        "title": "Director",
        "account_name": "Acme Corp",
        "date_entered": "2023-01-01T10:00:00Z",
        "date_modified": "2023-06-01T12:00:00Z",
        "_acl": {"fields": {}} # Should be ignored
    }
    result = map_contact(raw)
    
    assert result["provider_id"] == "sugarcrm"
    assert result["external_id"] == "sugar-123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "primary@example.com"
    assert result["phone"] == "555-0101"
    assert result["job_title"] == "Director"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {
        "date_entered": "2023-01-01T10:00:00Z",
        "date_modified": "2023-06-01T12:00:00Z"
    }

def test_map_contact_name_derivation_fallback():
    # Test fallback to first/last then email
    raw_fl = {
        "id": "id-2",
        "first_name": "Alice",
        "last_name": "Smith"
    }
    assert map_contact(raw_fl)["full_name"] == "Alice Smith"

    raw_email = {
        "id": "id-3",
        "email1": "no-name@example.com"
    }
    assert map_contact(raw_email)["full_name"] == "no-name@example.com"

def test_map_contact_invalid_id_raises_value_error():
    with pytest.raises(ValueError, match="missing 'id'"):
        map_contact({"full_name": "No ID"})

def test_map_contact_underivable_name_raises_value_error():
    with pytest.raises(ValueError, match="no derivable full_name"):
        map_contact({"id": "id-only"})

def test_map_contact_invalid_email_becomes_none():
    raw = {
        "id": "sugar-456",
        "full_name": "Bad Email User",
        "email1": "not-an-email-at-all"
    }
    result = map_contact(raw)
    assert result["full_name"] == "Bad Email User"
    assert result["primary_email"] is None

def test_map_contact_phone_priority():
    raw = {
        "id": "p-1",
        "full_name": "Phone Test",
        "phone_work": "",
        "phone_mobile": "123-456"
    }
    assert map_contact(raw)["phone"] == "123-456"

    raw_work = {
        "id": "p-2",
        "full_name": "Phone Test 2",
        "phone_work": "999",
        "phone_mobile": "123-456"
    }
    assert map_contact(raw_work)["phone"] == "999"

def test_map_contact_email_selection_logic():
    # Test primary flag selection
    raw = {
        "id": "e-1",
        "full_name": "Email Test",
        "email": [
            {"email_address": "first@test.com", "primary_address": False},
            {"email_address": "second@test.com", "primary_address": True}
        ]
    }
    assert map_contact(raw)["primary_email"] == "second@test.com"

    # Test fallback to first in list if no primary
    raw_no_prim = {
        "id": "e-2",
        "full_name": "Email Test 2",
        "email": [
            {"email_address": "only@test.com", "primary_address": False}
        ]
    }
    assert map_contact(raw_no_prim)["primary_email"] == "only@test.com"