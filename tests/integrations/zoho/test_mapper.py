import pytest
from src.integrations.zoho.mapper import map_zoho_contact

def test_map_zoho_contact_success():
    """Tests a full record with all fields and an object-based Account_Name."""
    record = {
        "id": "zoho_123",
        "Full_Name": "  John Doe  ",
        "Email": "JOHN.DOE@example.com",
        "Phone": "123-456",
        "Title": "Manager",
        "Account_Name": {"name": "Acme Corp", "id": "acc_001"},
        "Industry": "Software",
        "$approved": True,
        "Owner": {"name": "Admin"}
    }
    
    result = map_zoho_contact(record)
    
    assert result["provider_id"] == "zoho"
    assert result["external_id"] == "zoho_123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john.doe@example.com"
    assert result["phone"] == "123-456"
    assert result["job_title"] == "Manager"
    assert result["company_name"] == "Acme Corp"
    # Custom fields check: exclude consumed and metadata
    assert result["custom_fields"] == {"Industry": "Software"}
    assert "$approved" not in result["custom_fields"]
    assert "Owner" not in result["custom_fields"]

def test_full_name_derivation_logic():
    # Fallback to First/Last
    rec1 = {"id": "1", "First_Name": "Jane", "Last_Name": "Smith"}
    assert map_zoho_contact(rec1)["full_name"] == "Jane Smith"
    
    # Fallback to Email
    rec2 = {"id": "2", "Email": "anon@example.com"}
    assert map_zoho_contact(rec2)["full_name"] == "anon@example.com"
    
    # Fail if nothing
    with pytest.raises(ValueError, match="no derivable full_name"):
        map_zoho_contact({"id": "3"})

def test_email_validation():
    # Valid email
    rec_valid = {"id": "1", "Full_Name": "User", "Email": " VALID@test.com "}
    assert map_zoho_contact(rec_valid)["primary_email"] == "valid@test.com"
    
    # Invalid email maps to None but doesn't crash mapping
    rec_invalid = {"id": "2", "Full_Name": "User", "Email": "not-an-email"}
    res = map_zoho_contact(rec_invalid)
    assert res["primary_email"] is None
    assert res["full_name"] == "User"

def test_company_name_variants():
    # String account name
    res_str = map_zoho_contact({"id": "1", "Full_Name": "U", "Account_Name": "  Plain Inc "})
    assert res_str["company_name"] == "Plain Inc"
    
    # Null account name
    res_null = map_zoho_contact({"id": "2", "Full_Name": "U", "Account_Name": None})
    assert res_null["company_name"] is None

def test_missing_id_raises():
    with pytest.raises(ValueError, match="missing required 'id'"):
        map_zoho_contact({"Full_Name": "John"})

def test_phone_mobile_fallback():
    # Phone takes precedence
    rec1 = {"id": "1", "Full_Name": "U", "Phone": "111", "Mobile": "222"}
    assert map_zoho_contact(rec1)["phone"] == "111"
    
    # Mobile fallback
    rec2 = {"id": "2", "Full_Name": "U", "Phone": None, "Mobile": "222"}
    assert map_zoho_contact(rec2)["phone"] == "222"