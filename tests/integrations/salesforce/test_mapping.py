import pytest
from src.integrations.salesforce.mapping import salesforce_contact_to_incoming

def test_mapping_full_name_from_name():
    raw = {
        "Id": "0031",
        "Name": " Jane Doe ",
        "Email": "JANE@example.com",
        "Account": {"Name": "Acme Corp"}
    }
    mapped = salesforce_contact_to_incoming(raw)
    assert mapped["full_name"] == "Jane Doe"
    assert mapped["primary_email"] == "jane@example.com"
    assert mapped["company_name"] == "Acme Corp"

def test_mapping_full_name_fallback():
    raw = {
        "Id": "0032",
        "FirstName": "John",
        "LastName": "Smith",
        "Phone": "555-1234"
    }
    mapped = salesforce_contact_to_incoming(raw)
    assert mapped["full_name"] == "John Smith"
    assert mapped["phone"] == "555-1234"

def test_mapping_invalid_email_becomes_none(caplog):
    raw = {
        "Id": "0033",
        "Name": "Bad Email",
        "Email": "not-an-email"
    }
    mapped = salesforce_contact_to_incoming(raw)
    assert mapped["primary_email"] is None
    assert "invalid email format" in caplog.text

def test_mapping_missing_id_raises_value_error():
    raw = {"Name": "No ID"}
    with pytest.raises(ValueError, match="missing a valid 'Id'"):
        salesforce_contact_to_incoming(raw)

def test_mapping_custom_fields():
    raw = {
        "Id": "0034",
        "Name": "Custom Guy",
        "Department": "Engineering",
        "Custom_Field__c": "SpecialValue",
        "attributes": {"type": "Contact"}
    }
    mapped = salesforce_contact_to_incoming(raw)
    assert mapped["custom_fields"] == {
        "Department": "Engineering",
        "Custom_Field__c": "SpecialValue"
    }