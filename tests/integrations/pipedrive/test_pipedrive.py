import pytest
from unittest.mock import MagicMock, patch
from src.integrations.pipedrive import fetch
from src.integrations.pipedrive.mapper import map_pipedrive_person

def test_pipedrive_mapping_logic():
    """Verify the PipedriveContactMapping follows all derivation rules."""
    sample_person = {
        "id": 123,
        "name": " John Doe ",
        "email": [
            {"value": "work@example.com", "primary": False},
            {"value": "PRIMARY@Example.com", "primary": True}
        ],
        "job_title": "Engineer",
        "org_name": "Acme Corp",
        "phone": "555-1234",
        "custom_field_x": "secret_val"
    }
    
    result = map_pipedrive_person(sample_person)
    
    assert result["external_id"] == "123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "primary@example.com"
    assert result["company_name"] == "Acme Corp"
    assert result["job_title"] == "Engineer"
    assert "custom_field_x" in result["custom_fields"]
    assert "phone" not in result["custom_fields"]  # Discarded key

def test_fetch_pagination(monkeypatch):
    """Verify that fetch handles multi-page results correctly."""
    
    # Mock environment variables
    monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "fake-token")
    monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "fake-domain")
    
    # Page 1 mock response
    page1 = {
        "success": True,
        "data": [{"id": 1, "name": "User 1"}],
        "additional_data": {
            "pagination": {
                "more_items_in_collection": True,
                "next_start": 1
            }
        }
    }
    # Page 2 mock response
    page2 = {
        "success": True,
        "data": [{"id": 2, "name": "User 2"}],
        "additional_data": {
            "pagination": {
                "more_items_in_collection": False
            }
        }
    }

    mock_get = MagicMock()
    # Configure sequence of returns for pagination
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: page1),
        MagicMock(status_code=200, json=lambda: page2)
    ]
    
    with patch("httpx.get", mock_get):
        # We don't need a real get_stored for this fetch implementation
        get_stored = lambda dt: []
        results = fetch(get_stored)

        assert len(results) == 2
        assert results[0]["data"]["external_id"] == "1"
        assert results[1]["data"]["external_id"] == "2"
        # Verify params of second call for start offset
        args, kwargs = mock_get.call_args_list[1]
        assert kwargs["params"]["start"] == 1
        assert mock_get.call_count == 2


def test_fetch_environment_validation(monkeypatch):
    """Verify fetch raises RuntimeError if env vars are missing."""
    monkeypatch.delenv("PIPEDRIVE_API_TOKEN", raising=False)
    monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "acme")

    with pytest.raises(RuntimeError) as excinfo:
        fetch(lambda dt: [])
    assert "PIPEDRIVE_API_TOKEN" in str(excinfo.value)

def test_fetch_skip_and_log(monkeypatch):
    """Verify skip-and-log policy when mapping raises ValueError."""
    monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "fake-token")
    monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "fake-domain")
    
    page = {
        "success": True,
        "data": [
            {"id": 1, "name": "Valid"},
            {"id": 2, "name": "Invalid"}
        ],
        "additional_data": {"pagination": {"more_items_in_collection": False}}
    }

    def mock_mapper(person):
        if person["id"] == 2:
            raise ValueError("Bad data")
        return {"external_id": str(person["id"])}

    with patch("httpx.get", return_value=MagicMock(status_code=200, json=lambda: page)):
        with patch("src.integrations.pipedrive.map_pipedrive_person", side_effect=mock_mapper):
            results = fetch(lambda dt: [])
            assert len(results) == 1
            assert results[0]["data"]["external_id"] == "1"