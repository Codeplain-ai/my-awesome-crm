import pytest
from src.integrations.salesforce.mapping import map_contact_record

def test_map_complete_record():
    raw = {
        "attributes": {"type": "Contact", "url": "/services/data/v60.0/sobjects/Contact/003..."},
        "Id": "003Qy0000085W6SIAU",
        "Name": "John Doe",
        "Email": "JOHN.DOE@example.com ",
        "Phone": "+1-555-010-999",
        "MobilePhone": "555-0000",
        "Title": "Engineering Manager",
        "Account": {
            "attributes": {"type": "Account", "url": "/..."},
            "Name": "Acme Corp"
        },
        "Department": "Platform",
        "Birthdate": "1990-01-01"
    }
    
    result = map_contact_record(raw)
    
    assert result["provider_id"] == "salesforce"
    assert result["external_id"] == "003Qy0000085W6SIAU"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john.doe@example.com"
    assert result["phone"] == "+1-555-010-999"
    assert result["job_title"] == "Engineering Manager"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {"Department": "Platform", "Birthdate": "1990-01-01"}

def test_name_derivation_fallback():
    # Case: Name is missing, use FirstName + LastName
    raw = {
        "Id": "SF001",
        "FirstName": " Jane ",
        "LastName": "Smith "
    }
    result = map_contact_record(raw)
    assert result["full_name"] == "Jane Smith"

def test_missing_id_raises_value_error():
    raw = {"Name": "No Id"}
    with pytest.raises(ValueError, match="missing required 'Id'"):
        map_contact_record(raw)

def test_underivable_name_raises_value_error():
    raw = {"Id": "SF002", "Email": "anon@example.com"}
    with pytest.raises(ValueError, match="no derivable name"):
        map_contact_record(raw)

def test_invalid_email_maps_to_none(caplog):
    raw = {
        "Id": "SF003",
        "Name": "Bad Email User",
        "Email": "not-an-email"
    }
    result = map_contact_record(raw)
    assert result["primary_email"] is None
    assert "invalid email" in caplog.text
    assert "SF003" in caplog.text

def test_phone_priority():
    # Phone present, MobilePhone present -> Use Phone
    raw = {"Id": "P1", "Name": "N", "Phone": "123", "MobilePhone": "456"}
    assert map_contact_record(raw)["phone"] == "123"
    
    # Phone missing, MobilePhone present -> Use MobilePhone
    raw2 = {"Id": "P2", "Name": "N", "Phone": None, "MobilePhone": "456"}
    assert map_contact_record(raw2)["phone"] == "456"

def test_company_name_extraction():
    # Nested Account name
    raw = {"Id": "C1", "Name": "N", "Account": {"Name": " Global Inc "}}
    assert map_contact_record(raw)["company_name"] == "Global Inc"
    
    # Account is None
    raw2 = {"Id": "C2", "Name": "N", "Account": None}
    assert map_contact_record(raw2)["company_name"] is None

def test_custom_fields_excludes_metadata():
    raw = {
        "Id": "X1",
        "Name": "N",
        "attributes": {"foo": "bar"},
        "Custom_Field__c": "Value",
        "Account": {"attributes": {}, "Name": "A"}
    }
    result = map_contact_record(raw)
    # Account and attributes should not be in custom_fields
    assert "Custom_Field__c" in result["custom_fields"]
    assert "attributes" not in result["custom_fields"]
    assert "Account" not in result["custom_fields"]