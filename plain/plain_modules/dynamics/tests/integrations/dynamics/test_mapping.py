import pytest
from src.integrations.dynamics.mapping import map_dynamics_contact

def test_map_valid_contact_full():
    raw = {
        "contactid": "guid-123",
        "fullname": "  John Doe  ",
        "emailaddress1": "JOHN@Example.com",
        "telephone1": "123-456",
        "jobtitle": "Engineer",
        "parentcustomerid_account": {"name": "Acme Corp"},
        "other_field": "val",
        "@odata.etag": "W/123"
    }
    result = map_dynamics_contact(raw)
    
    assert result["provider_id"] == "dynamics"
    assert result["external_id"] == "guid-123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john@example.com"
    assert result["phone"] == "123-456"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {"other_field": "val"}

def test_map_full_name_derivation_from_parts():
    raw = {
        "contactid": "guid-2",
        "firstname": "Jane",
        "lastname": "Smith"
    }
    result = map_dynamics_contact(raw)
    assert result["full_name"] == "Jane Smith"

def test_map_missing_id_raises_value_error():
    raw = {"fullname": "No ID"}
    with pytest.raises(ValueError, match="missing 'contactid'"):
        map_dynamics_contact(raw)

def test_map_underivable_name_raises_value_error():
    raw = {"contactid": "guid-3"}
    with pytest.raises(ValueError, match="no derivable full_name"):
        map_dynamics_contact(raw)

def test_map_invalid_email_becomes_none():
    raw = {
        "contactid": "guid-4",
        "fullname": "Bad Email",
        "emailaddress1": "not-an-email"
    }
    result = map_dynamics_contact(raw)
    assert result["primary_email"] is None
    # Rest of fields should still map
    assert result["full_name"] == "Bad Email"

def test_map_phone_fallback():
    raw = {
        "contactid": "guid-5",
        "fullname": "Phone Test",
        "mobilephone": "987-654"
    }
    # telephone1 is missing, should use mobilephone
    result = map_dynamics_contact(raw)
    assert result["phone"] == "987-654"

def test_map_odata_metadata_filtered():
    raw = {
        "contactid": "guid-6",
        "fullname": "Metadata Test",
        "@odata.context": "context",
        "firstname@OData.Community.Display.V1.FormattedValue": "Jane",
        "real_custom": "keep me"
    }
    result = map_dynamics_contact(raw)
    assert result["custom_fields"] == {"real_custom": "keep me"}