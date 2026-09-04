import pytest
from unittest.mock import MagicMock, patch
import httpx
from src.integrations.copper import fetch
from src.integrations.copper.mapping import map_copper_person_to_contact

def test_mapping_external_id_derivation():
    # Case: Number to string
    assert map_copper_person_to_contact({"id": 27140442})["external_id"] == "27140442"
    # Case: Missing id
    assert map_copper_person_to_contact({})["external_id"] is None
    # Case: Empty id string (though Copper says number, mapping handles best effort)
    assert map_copper_person_to_contact({"id": " "})["external_id"] is None

def test_mapping_full_record():
    raw = {
        "id": 123,
        "name": " Jane Doe ",
        "title": "Engineer",
        "company_name": "Acme Corp",
        "emails": [{"email": " JANE@example.com ", "category": "work"}],
        "date_created": 1600000000,
        "date_modified": 1600000001,
    }
    mapped = map_copper_person_to_contact(raw)
    assert mapped["external_id"] == "123"
    assert mapped["full_name"] == "Jane Doe"
    assert mapped["primary_email"] == "jane@example.com"
    assert mapped["job_title"] == "Engineer"
    assert mapped["company_name"] == "Acme Corp"
    assert mapped["custom_fields"]["date_created"] == 1600000000

def test_mapping_name_derivation():
    # Case: No 'name', use first/last
    raw = {"id": 1, "first_name": "John", "last_name": "Smith"}
    assert map_copper_person_to_contact(raw)["full_name"] == "John Smith"
    
    # Case: Empty name and first/last
    assert map_copper_person_to_contact({"id": 2})["full_name"] == ""

def test_mapping_email_selection():
    raw = {
        "id": 1,
        "emails": [
            {"email": "", "category": "work"},
            {"email": "primary@test.com", "category": "personal"},
            {"email": "secondary@test.com", "category": "other"}
        ]
    }
    assert map_copper_person_to_contact(raw)["primary_email"] == "primary@test.com"

def test_fetch_missing_credentials():
    with patch("os.environ.get", return_value=None):
        with pytest.raises(RuntimeError) as excinfo:
            fetch(lambda dt: [])
        assert "COPPER_API_KEY" in str(excinfo.value)
        assert "COPPER_USER_EMAIL" in str(excinfo.value)

@patch("os.environ.get")
def test_fetch_pagination(mock_env_get):
    mock_env_get.side_effect = lambda k: "fake_val" if "COPPER" in k else None
    
    with patch("httpx.Client.post") as mock_post:
        # Scenario: Page 1 returns 200 items (full page), Page 2 returns 1 (partial).
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = [{"id": i} for i in range(200)]
        
        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = [{"id": 999}]
        
        mock_post.side_effect = [mock_response_1, mock_response_2]

        results = fetch(lambda dt: [])
        
        assert len(results) == 201
        assert results[0]["data"]["external_id"] == "0"
        assert results[200]["data"]["external_id"] == "999"
        assert mock_post.call_count == 2

@patch("os.environ.get")
def test_fetch_skip_and_log(mock_env_get):
    mock_env_get.side_effect = lambda k: "fake_val" if "COPPER" in k else None
    
    # Mock mapping to raise ValueError for one record
    # Patch it where it is imported/consumed in __init__.py
    with patch("src.integrations.copper.map_copper_person_to_contact") as mock_map:
        mock_map.side_effect = [
            {"external_id": "1"},
            ValueError("Bad record"),
            {"external_id": "3"}
        ]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        with patch("httpx.Client.post", return_value=mock_response):
            results = fetch(lambda dt: [])
            assert len(results) == 2
            assert results[0]["data"]["external_id"] == "1"
            assert results[1]["data"]["external_id"] == "3"