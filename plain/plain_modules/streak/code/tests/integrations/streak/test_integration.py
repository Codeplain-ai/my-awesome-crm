import pytest
from unittest.mock import MagicMock, patch
from src.integrations.streak.mapping import map_contact
from src.integrations.streak import fetch

def test_mapping_full_record():
    payload = {
        "key": "contact_1",
        "fullName": "  John Doe  ",
        "emailAddresses": ["John@Example.com", "other@work.com"],
        "title": "Engineer",
        "creationTimestamp": 123456789,
        "lastSavedTimestamp": 987654321,
        "other": "Should not be in custom_fields"
    }
    result = map_contact(payload)
    
    assert result["provider_id"] == "streak"
    assert result["external_id"] == "contact_1"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john@example.com"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] is None
    assert result["custom_fields"] == {
        "creationTimestamp": 123456789,
        "lastSavedTimestamp": 987654321
    }

def test_mapping_name_fallbacks():
    # Test fallback to given/family
    p1 = {"givenName": "Jane", "familyName": "Smith"}
    assert map_contact(p1)["full_name"] == "Jane Smith"
    
    # Test fallback to email
    p2 = {"emailAddresses": ["fallback@test.com"]}
    assert map_contact(p2)["full_name"] == "fallback@test.com"
    
    # Test absolute fallback
    p3 = {}
    assert map_contact(p3)["full_name"] == ""

@patch("src.integrations.streak.StreakClient")
@patch.dict("os.environ", {"STREAK_API_KEY": "test-key"})
def test_fetch_orchestration(MockClient):
    # Setup mocks
    mock_instance = MockClient.return_value
    mock_instance.list_teams.return_value = [{"key": "t1"}]
    mock_instance.list_contacts.return_value = [
        {"key": "c1", "fullName": "Contact One"},
        {"key": "c2", "fullName": "Contact Two"}
    ]
    
    def get_stored(dt): return []
    
    results = fetch(get_stored)
    
    assert len(results) == 2
    assert results[0]["data"]["external_id"] == "c1"
    assert results[1]["data"]["full_name"] == "Contact Two"
    assert results[0]["data_type"] == "contact"

@patch("src.integrations.streak.StreakClient")
@patch.dict("os.environ", {"STREAK_API_KEY": "test-key"})
def test_fetch_skip_on_mapping_error(MockClient):
    mock_instance = MockClient.return_value
    mock_instance.list_teams.return_value = [{"key": "t1"}]
    mock_instance.list_contacts.return_value = [
        {"key": "c1", "fullName": "Valid"},
        {"key": "c2", "fullName": "Invalid"}
    ]
    
    # Force mapping error for c2. Patch where it is consumed (in __init__.py).
    with patch("src.integrations.streak.map_contact") as mock_map:
        mock_map.side_effect = [
            {"external_id": "c1"},
            ValueError("Simulated mapping error")
        ]
        
        results = fetch(lambda dt: [])
        
        # Should only have one record, second one skipped via batch policy
        assert len(results) == 1
        assert results[0]["data"]["external_id"] == "c1"

def test_fetch_raises_on_missing_env():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing STREAK_API_KEY"):
            fetch(lambda dt: [])

def test_fetch_raises_on_empty_env():
    with patch.dict("os.environ", {"STREAK_API_KEY": ""}):
        with pytest.raises(RuntimeError, match="Missing STREAK_API_KEY"):
            fetch(lambda dt: [])

@patch("src.integrations.streak.StreakClient")
@patch.dict("os.environ", {"STREAK_API_KEY": "test-key"})
def test_fetch_api_failure_propagation(MockClient):
    mock_instance = MockClient.return_value
    mock_instance.list_teams.side_effect = RuntimeError("API Down")
    
    with pytest.raises(RuntimeError, match="Streak connection failed: API Down"):
        fetch(lambda dt: [])