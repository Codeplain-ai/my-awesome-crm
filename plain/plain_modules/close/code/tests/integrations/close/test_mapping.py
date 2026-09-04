from src.integrations.close.mapping import map_contact

def test_map_contact_standard_fields():
    source = {
        "id": "cont_1",
        "name": " Alice Smith ",
        "title": "Manager",
        "lead_id": "lead_123",
        "organization_id": "org_456",
        "emails": [{"email": "ALICE@example.com"}],
        "date_created": "2024-01-01T12:00:00Z"
    }
    res = map_contact(source)
    assert res["full_name"] == "Alice Smith"
    assert res["primary_email"] == "alice@example.com"
    assert res["job_title"] == "Manager"
    assert res["custom_fields"]["lead_id"] == "lead_123"
    assert res["external_id"] == "cont_1"

def test_map_contact_name_fallback():
    # If name is null, use email
    source = {
        "id": "cont_2",
        "name": None,
        "emails": [{"email": "bob@example.com"}]
    }
    res = map_contact(source)
    assert res["full_name"] == "bob@example.com"

def test_map_contact_empty_states():
    source = {"id": "cont_3"}
    res = map_contact(source)
    assert res["full_name"] == ""
    assert res["primary_email"] is None
    assert res["job_title"] is None
    assert res["company_name"] is None