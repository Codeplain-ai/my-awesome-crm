import pytest
from src.integrations.streak.mapping import map_streak_contact

def test_map_streak_contact_full():
    """Tests a record with all fields populated."""
    raw = {
        "key": "c123",
        "fullName": "Jane Doe",
        "emailAddresses": ["JANE@example.com", "other@example.com"],
        "phoneNumbers": ["555-0101"],
        "title": "Engineer",
        "creationTimestamp": 1623912000000,
        "lastSavedTimestamp": 1623912100000
    }
    
    result = map_streak_contact(raw)
    
    assert result.provider_id == "streak"
    assert result.external_id == "c123"
    assert result.full_name == "Jane Doe"
    assert result.primary_email == "jane@example.com"  # Normalized
    assert result.phone == "555-0101"
    assert result.job_title == "Engineer"
    assert result.company_name is None
    assert result.custom_fields["creationTimestamp"] == 1623912000000

def test_map_streak_name_fallbacks():
    """Tests the chain: fullName -> given/family -> email."""
    # Fallback to given/family
    raw2 = {
        "key": "c2",
        "givenName": "Bob",
        "familyName": "Smith"
    }
    assert map_streak_contact(raw2).full_name == "Bob Smith"

    # Fallback to email
    raw3 = {
        "key": "c3",
        "emailAddresses": ["  contact@example.com  "]
    }
    assert map_streak_contact(raw3).full_name == "contact@example.com"

def test_map_streak_invalid_email_handling():
    """An invalid email should result in primary_email=None but not a skip."""
    raw = {
        "key": "c4",
        "fullName": "Bad Email User",
        "emailAddresses": ["not-an-email"]
    }
    result = map_streak_contact(raw)
    assert result.full_name == "Bad Email User"
    assert result.primary_email is None

def test_map_streak_skips_missing_key():
    """Records with no key must raise ValueError."""
    with pytest.raises(ValueError, match="missing required 'key'"):
        map_streak_contact({"fullName": "No Key"})

def test_map_streak_skips_missing_name_and_email():
    """Records with no name info and no email info must raise ValueError."""
    with pytest.raises(ValueError, match="no derivable full_name"):
        map_streak_contact({"key": "c5"})

def test_map_streak_phone_selection():
    """Tests that the first non-empty phone is picked."""
    raw = {
        "key": "c6",
        "fullName": "Phone Test",
        "phoneNumbers": ["", "  ", "123-456", "789"]
    }
    result = map_streak_contact(raw)
    assert result.phone == "123-456"