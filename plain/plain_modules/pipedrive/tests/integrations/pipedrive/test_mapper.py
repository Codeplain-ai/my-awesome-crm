import pytest
import os
from unittest.mock import MagicMock, patch
from src.integrations.pipedrive import fetch_contacts
from src.integrations.pipedrive.mapper import map_pipedrive_person

def test_map_complete_record():
    raw = {
        "id": 123,
        "name": " John Doe ",
        "email": [{"value": "John@Example.com", "primary": True}],
        "phone": [{"value": "555-1234", "primary": True}],
        "job_title": "Engineer",
        "org_name": "Acme Corp",
        "custom_hex_key": "abc-123"
    }
    result = map_pipedrive_person(raw)
    
    assert result["provider_id"] == "pipedrive"
    assert result["external_id"] == "123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john@example.com"
    assert result["phone"] == "555-1234"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {"custom_hex_key": "abc-123"}

def test_map_missing_id_raises_value_error():
    with pytest.raises(ValueError, match="missing 'id'"):
        map_pipedrive_person({"name": "No ID"})

def test_map_name_derivation_from_parts():
    raw = {
        "id": 456,
        "first_name": "Jane",
        "last_name": "Smith"
    }
    result = map_pipedrive_person(raw)
    assert result["full_name"] == "Jane Smith"

def test_map_invalid_name_raises_value_error():
    raw = {"id": 789, "name": "  ", "first_name": None, "last_name": ""}
    with pytest.raises(ValueError, match="missing derivable name"):
        map_pipedrive_person(raw)

def test_map_email_validation():
    # Invalid email should map to None but not fail the record
    raw = {
        "id": 101,
        "name": "Bad Email",
        "email": [{"value": "not-an-email", "primary": True}]
    }
    result = map_pipedrive_person(raw)
    assert result["primary_email"] is None
    assert result["full_name"] == "Bad Email"

def test_map_org_fallback():
    raw = {
        "id": 202,
        "name": "Org Test",
        "org_id": {"name": "Nested Org"}
    }
    result = map_pipedrive_person(raw)
    assert result["company_name"] == "Nested Org"

def test_map_phone_selection():
    raw = {
        "id": 303,
        "name": "Phone Test",
        "phone": [
            {"value": "111", "primary": False},
            {"value": "222", "primary": True}
        ]
    }
    result = map_pipedrive_person(raw)
    assert result["phone"] == "222"

@patch("src.integrations.pipedrive.httpx.Client")
def test_fetch_contacts_pagination_and_skip(mock_client_class):
    # Setup environment
    os.environ["PIPEDRIVE_API_TOKEN"] = "fake-token"
    os.environ["PIPEDRIVE_COMPANY_DOMAIN"] = "test-co"

    # Mock responses for two pages
    # Page 1: One good record, one bad (missing name)
    page1 = {
        "success": True,
        "data": [
            {"id": 1, "name": "Valid One"},
            {"id": 2} # Missing name -> ValueError
        ],
        "additional_data": {
            "pagination": {
                "more_items_in_collection": True,
                "next_start": 2
            }
        }
    }
    # Page 2: One good record, no more items
    page2 = {
        "success": True,
        "data": [
            {"id": 3, "name": "Valid Two"}
        ],
        "additional_data": {
            "pagination": {
                "more_items_in_collection": False
            }
        }
    }

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    mock_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: page1, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: page2, raise_for_status=lambda: None)
    ]

    results = fetch_contacts()

    assert len(results) == 2
    assert results[0]["external_id"] == "1"
    assert results[0]["full_name"] == "Valid One"
    assert results[1]["external_id"] == "3"
    assert results[1]["full_name"] == "Valid Two"
    
    # Verify two calls were made with correct start params
    assert mock_client.get.call_count == 2
    args1, kwargs1 = mock_client.get.call_args_list[0]
    assert kwargs1["params"]["start"] == 0
    args2, kwargs2 = mock_client.get.call_args_list[1]
    assert kwargs2["params"]["start"] == 2

def test_fetch_contacts_missing_env_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="PIPEDRIVE_API_TOKEN"):
            fetch_contacts()