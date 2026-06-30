import pytest
from src.integrations.streak.mapping import map_streak_contact

def test_map_streak_contact_full():
    streak_record = {
        "key": "contact_1",
        "fullName": " Jane Doe ",
        "givenName": "Jane",
        "familyName": "Doe",
        "emailAddresses": ["JANE@example.com ", "other@test.com"],
        "title": "Engineer",
        "creationTimestamp": 1625097600000,
        "lastSavedTimestamp": 1625184000000
    }
    
    result = map_streak_contact(streak_record)
    
    assert result["provider_id"] == "streak"
    assert result["external_id"] == "contact_1"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] == "jane@example.com"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] is None
    assert result["custom_fields"]["creationTimestamp"] == 1625097600000
    assert result["custom_fields"]["lastSavedTimestamp"] == 1625184000000

def test_map_streak_contact_name_derivation_given_family():
    streak_record = {
        "key": "contact_2",
        "fullName": None,
        "givenName": "Alice",
        "familyName": "Smith",
        "emailAddresses": []
    }
    result = map_streak_contact(streak_record)
    assert result["full_name"] == "Alice Smith"

def test_map_streak_contact_name_derivation_email():
    streak_record = {
        "key": "contact_3",
        "fullName": "",
        "givenName": None,
        "familyName": None,
        "emailAddresses": [" bob@work.com"]
    }
    result = map_streak_contact(streak_record)
    assert result["full_name"] == "bob@work.com"

def test_map_streak_contact_empty():
    streak_record = {"key": "empty_one"}
    result = map_streak_contact(streak_record)
    assert result["full_name"] == ""
    assert result["primary_email"] is None
    assert result["job_title"] is None
    assert result["custom_fields"] == {}