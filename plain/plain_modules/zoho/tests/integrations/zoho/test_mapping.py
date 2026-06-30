from src.integrations.zoho.mapping import map_contact


def test_map_contact_full_name_variants():
    # 1. Uses Full_Name
    res = map_contact({"id": "1", "Full_Name": " Alice Smith "})
    assert res["full_name"] == "Alice Smith"

    # 2. Uses First + Last
    res = map_contact({"id": "2", "First_Name": "Bob", "Last_Name": "Jones"})
    assert res["full_name"] == "Bob Jones"

    # 3. Uses Email
    res = map_contact({"id": "3", "Email": "charlie@example.com"})
    assert res["full_name"] == "charlie@example.com"

    # 4. Fallback empty
    res = map_contact({"id": "4"})
    assert res["full_name"] == ""


def test_map_contact_email_normalization():
    res = map_contact({"id": "1", "Email": "  USER@Example.COM  "})
    assert res["primary_email"] == "user@example.com"
    
    res = map_contact({"id": "2", "Email": ""})
    assert res["primary_email"] is None


def test_map_contact_company_name():
    # Object shape
    res = map_contact({"id": "1", "Account_Name": {"name": " Acme Corp ", "id": "acc1"}})
    assert res["company_name"] == "Acme Corp"

    # String shape
    res = map_contact({"id": "2", "Account_Name": " Globex "})
    assert res["company_name"] == "Globex"

    # Missing/Null
    res = map_contact({"id": "3", "Account_Name": None})
    assert res["company_name"] is None


def test_map_contact_custom_fields():
    raw = {
        "id": "123",
        "Email": "test@test.com",
        "Title": "Manager",
        "Industry": "Tech",
        "Custom_Score": 42,
        "$approved": True,
        "Owner": {"name": "Admin"},
        "Account_Name": {"name": "Org"}
    }
    res = map_contact(raw)
    
    # Industry and Custom_Score should be in custom_fields
    assert res["custom_fields"] == {"Industry": "Tech", "Custom_Score": 42}
    # Consumed/System keys should NOT be in custom_fields
    assert "Email" not in res["custom_fields"]
    assert "Title" not in res["custom_fields"]
    assert "$approved" not in res["custom_fields"]
    assert "Owner" not in res["custom_fields"]
    assert "Account_Name" not in res["custom_fields"]


def test_map_contact_job_title():
    res = map_contact({"id": "1", "Title": " Software Engineer "})
    assert res["job_title"] == "Software Engineer"
    
    res = map_contact({"id": "2", "Title": ""})
    assert res["job_title"] is None