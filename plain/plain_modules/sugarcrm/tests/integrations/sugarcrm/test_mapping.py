import pytest
from src.integrations.sugarcrm.mapping import map_contact

def test_map_contact_full_name_derivation():
    # Test case 1: explicit full_name
    assert map_contact({"full_name": " John Doe "})["full_name"] == "John Doe"
    
    # Test case 2: fallback to name
    assert map_contact({"name": " Jane Doe "})["full_name"] == "Jane Doe"
    
    # Test case 3: first + last
    assert map_contact({"first_name": "Bob", "last_name": "Smith"})["full_name"] == "Bob Smith"
    
    # Test case 4: only last name
    assert map_contact({"last_name": "Prince"})["full_name"] == "Prince"
    
    # Test case 5: fallback to email
    assert map_contact({"email1": "test@example.com"})["full_name"] == "test@example.com"
    
    # Test case 6: empty everything
    assert map_contact({})["full_name"] == ""

def test_map_contact_email_selection():
    # Test case 1: primary in list
    raw = {
        "email": [
            {"email_address": "alt@example.com", "primary_address": False},
            {"email_address": "PRI@example.com", "primary_address": True}
        ]
    }
    assert map_contact(raw)["primary_email"] == "pri@example.com"
    
    # Test case 2: first in list if no primary
    raw = {
        "email": [
            {"email_address": "FIRST@example.com"},
            {"email_address": "second@example.com"}
        ]
    }
    assert map_contact(raw)["primary_email"] == "first@example.com"
    
    # Test case 3: fallback to email1
    raw = {"email1": "FLAT@example.com"}
    assert map_contact(raw)["primary_email"] == "flat@example.com"

def test_map_contact_custom_fields():
    raw = {
        "id": "123",
        "date_entered": "2023-01-01T00:00:00Z",
        "date_modified": "2023-02-01T00:00:00Z",
        "title": "Manager",
        "other_random_field": "ignore me",
        "_api_meta": "ignore me too"
    }
    result = map_contact(raw)
    cf = result["custom_fields"]
    assert cf["date_entered"] == "2023-01-01T00:00:00Z"
    assert cf["date_modified"] == "2023-02-01T00:00:00Z"
    assert "other_random_field" not in cf
    assert "title" not in cf