from src.integrations.copper.mapping import map_copper_person_to_contact

def test_mapping_logic_robustness():
    # Test record with full fields
    person = {
        "id": 555,
        "name": "Jane Doe",
        "title": "CTO",
        "company_name": "Tech Corp",
        "emails": [{"email": "jane@tech.corp", "category": "work"}],
        "date_created": 12345,
        "date_modified": 67890
    }
    mapped = map_copper_person_to_contact(person)
    assert mapped["external_id"] == "555"
    assert mapped["full_name"] == "Jane Doe"
    assert mapped["primary_email"] == "jane@tech.corp"
    assert mapped["job_title"] == "CTO"
    assert mapped["custom_fields"] == {"date_created": 12345, "date_modified": 67890}

def test_mapping_name_concatenation():
    # Only first/last name provided
    person = {"id": 1, "first_name": "Bob", "last_name": "Builder"}
    mapped = map_copper_person_to_contact(person)
    assert mapped["full_name"] == "Bob Builder"

def test_mapping_empty_email_list():
    person = {"id": 1, "emails": []}
    mapped = map_copper_person_to_contact(person)
    assert mapped["primary_email"] is None

def test_mapping_id_string_conversion():
    person = {"id": 0}
    mapped = map_copper_person_to_contact(person)
    assert mapped["external_id"] == "0"