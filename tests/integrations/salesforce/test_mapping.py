import pytest
from src.integrations.salesforce.mapping import salesforce_contact_to_incoming

def test_mapping_full_payload():
    """Test mapping with all fields present including nested account and custom fields."""
    sf_data = {
        "attributes": {"type": "Contact", "url": "/services/data/v59.0/sobjects/Contact/003P000001AmXYZ"},
        "Id": "003P000001AmXYZ",
        "Name": "John Doe",
        "Email": " JOHN.doe@Example.com ",
        "Phone": "+1-555-010-999",
        "Title": "Chief Officer",
        "Account": {"Name": "Acme Corp"},
        "Custom_Score__c": 42,
        "Department": "Engineering"
    }
    
    result = salesforce_contact_to_incoming(sf_data)
    
    assert result["provider_id"] == "salesforce"
    assert result["external_id"] == "003P000001AmXYZ"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john.doe@example.com"
    assert result["phone"] == "+1-555-010-999"
    assert result["job_title"] == "Chief Officer"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {"Custom_Score__c": 42, "Department": "Engineering"}

def test_mapping_name_fallback():
    """Test fallback to FirstName/LastName if Name is missing."""
    sf_data = {
        "Id": "003P001",
        "FirstName": " Jane ",
        "LastName": "Smith ",
        "Email": "jane@smith.com"
    }
    
    result = salesforce_contact_to_incoming(sf_data)
    assert result["full_name"] == "Jane Smith"

def test_mapping_missing_id_raises():
    """Mapping should fail if Id is missing."""
    sf_data = {"Name": "No ID"}
    with pytest.raises(ValueError, match="missing required field: Id"):
        salesforce_contact_to_incoming(sf_data)

def test_mapping_missing_name_raises():
    """Mapping should fail if no name information is available."""
    sf_data = {"Id": "003P002", "Email": "anon@example.com"}
    with pytest.raises(ValueError, match="no valid Name, FirstName, or LastName"):
        salesforce_contact_to_incoming(sf_data)

def test_mapping_minimal_fields():
    """Test mapping with only required fields and empty/null values for others."""
    sf_data = {
        "Id": "003P003",
        "Name": "Minimal Contact",
        "Account": None,
        "Email": "  "
    }
    
    result = salesforce_contact_to_incoming(sf_data)
    assert result["external_id"] == "003P003"
    assert result["full_name"] == "Minimal Contact"
    assert result["primary_email"] is None
    assert result["company_name"] is None
    assert result["custom_fields"] == {}