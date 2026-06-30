import pytest
from src.integrations.pipedrive.mapping import map_pipedrive_person_to_contact

def test_mapping_full_name_derivation():
    # Priority 1: name field
    res = map_pipedrive_person_to_contact({"id": 1, "name": " John Doe "})
    assert res["full_name"] == "John Doe"

    # Priority 2: first + last
    res = map_pipedrive_person_to_contact({"id": 2, "first_name": "Jane", "last_name": "Smith"})
    assert res["full_name"] == "Jane Smith"

    # Priority 3: empty
    res = map_pipedrive_person_to_contact({"id": 3})
    assert res["full_name"] == ""

def test_mapping_email_selection():
    # Pick primary
    person = {
        "id": 1,
        "email": [
            {"value": "work@test.com", "primary": False},
            {"value": "HOME@test.com", "primary": True}
        ]
    }
    res = map_pipedrive_person_to_contact(person)
    assert res["primary_email"] == "home@test.com"

    # Pick first if no primary
    person = {
        "id": 1,
        "email": [
            {"value": "first@test.com", "primary": False},
            {"value": "second@test.com", "primary": False}
        ]
    }
    res = map_pipedrive_person_to_contact(person)
    assert res["primary_email"] == "first@test.com"

def test_mapping_company_name():
    # Use org_name
    res = map_pipedrive_person_to_contact({"id": 1, "org_name": "Acme Corp"})
    assert res["company_name"] == "Acme Corp"

    # Use org_id.name
    res = map_pipedrive_person_to_contact({"id": 1, "org_id": {"name": "Nested Org"}})
    assert res["company_name"] == "Nested Org"

def test_custom_fields_exclusion():
    person = {
        "id": 123,
        "name": "Test",
        "custom_key_1": "val1",
        "custom_key_2": 42
    }
    res = map_pipedrive_person_to_contact(person)
    assert "custom_key_1" in res["custom_fields"]
    assert "custom_key_2" in res["custom_fields"]
    # Consumed keys should NOT be in custom_fields
    assert "id" not in res["custom_fields"]
    assert "name" not in res["custom_fields"]