import pytest
from src.integrations.dynamics.mapping import map_contact_record

def test_mapping_full_fields():
    raw = {
        "contactid": "guid-123",
        "fullname": " Jane Doe ",
        "firstname": "Jane",
        "lastname": "Doe",
        "emailaddress1": " JANE@example.com ",
        "jobtitle": "Engineer",
        "parentcustomerid_account": {"name": "Acme Corp"},
        "custom_prop": "val",
        "@odata.etag": "tag123"
    }
    mapped = map_contact_record(raw)
    
    assert mapped["external_id"] == "guid-123"
    assert mapped["full_name"] == "Jane Doe"
    assert mapped["primary_email"] == "jane@example.com"
    assert mapped["job_title"] == "Engineer"
    assert mapped["company_name"] == "Acme Corp"
    assert mapped["custom_fields"] == {"custom_prop": "val"}
    assert "fullname" not in mapped["custom_fields"]
    assert "@odata.etag" not in mapped["custom_fields"]

def test_mapping_name_derivation_fallback():
    # Fallback to first + last when fullname is missing
    raw = {
        "contactid": "guid-2",
        "firstname": "John",
        "lastname": "Smith"
    }
    mapped = map_contact_record(raw)
    assert mapped["full_name"] == "John Smith"

    # Total fallback to empty string
    raw_empty = {"contactid": "guid-3"}
    mapped_empty = map_contact_record(raw_empty)
    assert mapped_empty["full_name"] == ""

def test_mapping_custom_fields_metadata_filtering():
    raw = {
        "contactid": "id",
        "business_value": 42,
        "@odata.context": "drop-me",
        "jobtitle@OData.Community.Display.V1.FormattedValue": "drop-me"
    }
    mapped = map_contact_record(raw)
    assert mapped["custom_fields"] == {"business_value": 42}