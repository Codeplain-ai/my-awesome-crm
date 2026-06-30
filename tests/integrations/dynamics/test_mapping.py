from src.integrations.dynamics.mapping import map_contact

def test_map_contact_full_name_preference():
    source = {
        "contactid": "guid-1",
        "fullname": "  John Doe  ",
        "firstname": "John",
        "lastname": "Doe"
    }
    mapped = map_contact(source)
    assert mapped["full_name"] == "John Doe"

def test_map_contact_name_fallback():
    source = {
        "contactid": "guid-2",
        "fullname": None,
        "firstname": "Jane",
        "lastname": "Smith"
    }
    mapped = map_contact(source)
    assert mapped["full_name"] == "Jane Smith"

def test_map_contact_email_cleaning():
    source = {
        "contactid": "guid-3",
        "emailaddress1": "  USER@Example.COM  "
    }
    mapped = map_contact(source)
    assert mapped["primary_email"] == "user@example.com"

def test_map_contact_company_expansion():
    source = {
        "contactid": "guid-4",
        "parentcustomerid_account": {"name": "Acme Corp"}
    }
    mapped = map_contact(source)
    assert mapped["company_name"] == "Acme Corp"

def test_map_contact_custom_fields_filtering():
    source = {
        "contactid": "guid-5",
        "jobtitle": "Dev",
        "favorite_color": "blue",
        "@odata.etag": "123",
        "other@odata.annotation": "abc"
    }
    mapped = map_contact(source)
    assert mapped["custom_fields"] == {"favorite_color": "blue"}
    assert "jobtitle" not in mapped["custom_fields"]
    assert "@odata.etag" not in mapped["custom_fields"]