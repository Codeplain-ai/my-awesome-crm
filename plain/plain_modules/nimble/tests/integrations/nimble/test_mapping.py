import pytest
from src.integrations.nimble.mapping import map_contact

def test_map_contact_full_info():
    raw = {
        "id": "500",
        "record_type": "person",
        "fields": {
            "first name": [{"value": "Wilma"}],
            "last name": [{"value": "Flintstone"}],
            "email": [{"value": " WILMA@slater.com "}],
            "title": [{"value": "Reporter"}],
            "company": [{"value": "Bedrock News"}]
        }
    }
    mapped = map_contact(raw)
    assert mapped["provider_id"] == "nimble"
    assert mapped["external_id"] == "500"
    assert mapped["full_name"] == "Wilma Flintstone"
    assert mapped["primary_email"] == "wilma@slater.com"
    assert mapped["job_title"] == "Reporter"
    assert mapped["company_name"] == "Bedrock News"
    assert mapped["custom_fields"]["record_type"] == "person"

def test_map_contact_name_derivation_email():
    # No names, should fallback to email
    raw = {
        "id": "501",
        "fields": {
            "email": [{"value": "barney@rubble.com"}]
        }
    }
    mapped = map_contact(raw)
    assert mapped["full_name"] == "barney@rubble.com"

def test_map_contact_name_derivation_company():
    # No names or email, should fallback to company
    raw = {
        "id": "502",
        "fields": {
            "company": [{"value": "Slate Rock and Gravel"}]
        }
    }
    mapped = map_contact(raw)
    assert mapped["full_name"] == "Slate Rock and Gravel"

def test_map_contact_empty_values():
    raw = {
        "id": "503",
        "fields": {
            "first name": [{"value": ""}],
            "last name": [{"value": None}],
            "email": []
        }
    }
    mapped = map_contact(raw)
    assert mapped["full_name"] == ""
    assert mapped["primary_email"] is None
    assert mapped["job_title"] is None