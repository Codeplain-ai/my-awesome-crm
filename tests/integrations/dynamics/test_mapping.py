import pytest
from src.integrations.dynamics.mapping import map_contact

def test_map_contact_full():
    raw = {
        "contactid": "guid-123",
        "fullname": "  John Doe  ",
        "emailaddress1": "John.Doe@Example.Com",
        "jobtitle": "Engineer",
        "parentcustomerid_account": {"name": "Acme Corp"},
        "other_field": "value",
        "@odata.etag": "tag"
    }
    mapped = map_contact(raw)
    assert mapped["external_id"] == "guid-123"
    assert mapped["full_name"] == "John Doe"
    assert mapped["primary_email"] == "john.doe@example.com"
    assert mapped["job_title"] == "Engineer"
    assert mapped["company_name"] == "Acme Corp"
    assert mapped["custom_fields"] == {"other_field": "value"}

def test_map_contact_name_derivation():
    # No fullname, use first/last
    raw = {
        "contactid": "id2",
        "firstname": "Jane",
        "lastname": "Smith"
    }
    mapped = map_contact(raw)
    assert mapped["full_name"] == "Jane Smith"

    # Empty components
    raw = {"contactid": "id3", "firstname": "OnlyFirst"}
    assert map_contact(raw)["full_name"] == "OnlyFirst"

    # Nothing at all
    assert map_contact({"contactid": "id4"})["full_name"] == ""

def test_map_contact_nulls():
    raw = {
        "contactid": "id5",
        "fullname": None,
        "emailaddress1": None,
        "parentcustomerid_account": None
    }
    mapped = map_contact(raw)
    assert mapped["full_name"] == ""
    assert mapped["primary_email"] is None
    assert mapped["company_name"] is None
