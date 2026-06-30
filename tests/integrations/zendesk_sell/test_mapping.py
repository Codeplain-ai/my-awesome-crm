import pytest
from src.integrations.zendesk_sell.mapping import map_contact

def test_map_contact_organization():
    raw = {
        "id": 123,
        "is_organization": True,
        "name": " Acme Corp ",
        "email": "INFO@acme.com",
        "custom_fields": {"Sector": "Tech"}
    }
    mapped = map_contact(raw)
    assert mapped["provider_id"] == "zendesk_sell"
    assert mapped["external_id"] == "123"
    assert mapped["full_name"] == "Acme Corp"
    assert mapped["primary_email"] == "info@acme.com"
    assert mapped["custom_fields"]["Sector"] == "Tech"
    assert mapped["custom_fields"]["is_organization"] is True

def test_map_contact_person_with_first_last():
    raw = {
        "id": 456,
        "is_organization": False,
        "first_name": "John",
        "last_name": "Doe",
        "title": "Manager"
    }
    mapped = map_contact(raw)
    assert mapped["full_name"] == "John Doe"
    assert mapped["job_title"] == "Manager"

def test_map_contact_person_fallback_to_email():
    raw = {
        "id": 789,
        "is_organization": False,
        "email": " Ghost@Example.com "
    }
    mapped = map_contact(raw)
    # full_name uses raw trimmed email, primary_email uses lowercased trimmed
    assert mapped["full_name"] == "Ghost@Example.com"
    assert mapped["primary_email"] == "ghost@example.com"

def test_map_contact_missing_id():
    raw = {"name": "No ID"}
    mapped = map_contact(raw)
    assert mapped["external_id"] is None