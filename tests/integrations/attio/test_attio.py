import pytest
from unittest.mock import MagicMock, patch
from src.integrations.attio import fetch
from src.integrations.attio.mapping import map_attio_person_to_contact

SAMPLE_PERSON = {
    "id": {"record_id": "person_1"},
    "values": {
        "name": [{"full_name": " Alice Smith "}],
        "email_addresses": [{"email_address": "ALICE@example.com"}],
        "job_title": [{"value": "Engineer"}],
        "company": [{"target_record_id": "comp_1"}],
        "phone_numbers": [{"phone_number": "+12345"}],
        "linkedin": [{"value": "li/alice"}],
        "description": [{"value": "Test desc"}]
    }
}

def test_mapping_full_payload():
    result = map_attio_person_to_contact(SAMPLE_PERSON)
    assert result["external_id"] == "person_1"
    assert result["full_name"] == "Alice Smith"
    assert result["primary_email"] == "alice@example.com"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] is None
    assert result["custom_fields"] == {
        "company_record_id": "comp_1",
        "phone_number": "+12345",
        "linkedin": "li/alice",
        "description": "Test desc"
    }

def test_mapping_minimal_payload():
    minimal = {
        "id": {"record_id": "person_2"},
        "values": {}
    }
    result = map_attio_person_to_contact(minimal)
    assert result["external_id"] == "person_2"
    assert result["full_name"] == ""
    assert result["primary_email"] is None
    assert result["custom_fields"] == {
        "company_record_id": None,
        "phone_number": None,
        "linkedin": None,
        "description": None
    }

def test_mapping_name_derivation_from_parts():
    person = {
        "id": {"record_id": "p3"},
        "values": {
            "name": [{"first_name": "Bob ", "last_name": " Jones"}]
        }
    }
    result = map_attio_person_to_contact(person)
    assert result["full_name"] == "Bob Jones"

@patch("src.integrations.attio.client.AttioClient.query_people")
def test_fetch_error_handling(mock_query):
    # Test skip-and-log policy for ValueError during mapping
    mock_query.return_value = {
        "data": [
            {"id": {"record_id": "fail"}, "values": {}},
            SAMPLE_PERSON
        ]
    }
    with patch("src.integrations.attio.map_attio_person_to_contact") as mock_map:
        mock_map.side_effect = [ValueError("Bad data"), {"external_id": "person_1"}]
        with patch.dict("os.environ", {"ATTIO_ACCESS_TOKEN": "fake-token"}):
            records = fetch(lambda dt: [])
            # One skipped, one succeeded
            assert len(records) == 1

@patch("src.integrations.attio.client.AttioClient.query_people")
def test_fetch_pagination(mock_query):
    # Page 1: Full (500 records)
    # Page 2: 1 record (Total 501)
    mock_query.side_effect = [
        {"data": [SAMPLE_PERSON] * 500},
        {"data": [SAMPLE_PERSON]}
    ]

    # Mock environment variable for client init
    with patch.dict("os.environ", {"ATTIO_ACCESS_TOKEN": "fake-token"}):
        records = fetch(lambda dt: [])
        
        assert len(records) == 501
        assert records[0]["data_type"] == "contact"
        assert records[0]["data"]["external_id"] == "person_1"
        assert mock_query.call_count == 2

@patch("src.integrations.attio.client.AttioClient.query_people")
def test_fetch_empty(mock_query):
    mock_query.return_value = {"data": []}
    with patch.dict("os.environ", {"ATTIO_ACCESS_TOKEN": "fake-token"}):
        records = fetch(lambda dt: [])
        assert len(records) == 0