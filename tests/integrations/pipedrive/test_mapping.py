from __future__ import annotations

from src.integrations.pipedrive import map_contact


class TestMapContact:
    def test_maps_standard_person_fields_and_preserves_custom_values(self):
        person = {
            "id": 42,
            "name": "  Ada Lovelace  ",
            "first_name": "Ignored",
            "last_name": "Name",
            "email": [
                {"value": "  ADA@Example.COM ", "primary": True, "label": "work"},
                {"value": "other@example.com", "primary": False},
            ],
            "job_title": "Engineer",
            "org_name": "  Analytical Engines  ",
            "org_id": {"name": "Nested name"},
            "phone": [{"value": "555-0100"}],
            "website": "https://example.test",
            "custom_provider_value": {"flag": True},
        }

        original = person.copy()
        assert map_contact(person) == {
            "provider_id": "pipedrive",
            "external_id": "42",
            "full_name": "Ada Lovelace",
            "primary_email": "ada@example.com",
            "job_title": "Engineer",
            "company_name": "Analytical Engines",
            "custom_fields": {
                "website": "https://example.test",
                "custom_provider_value": {"flag": True},
            },
        }
        assert person == original

    def test_uses_name_parts_and_first_email_when_no_primary_is_marked(self):
        mapped = map_contact(
            {
                "id": "person-7",
                "name": "  ",
                "first_name": "  Grace ",
                "last_name": " Hopper  ",
                "email": [
                    {"value": "  GRACE@example.test  ", "primary": False},
                    {"value": "second@example.test", "primary": False},
                ],
            }
        )

        assert mapped["external_id"] == "person-7"
        assert mapped["full_name"] == "Grace Hopper"
        assert mapped["primary_email"] == "grace@example.test"
        assert mapped["company_name"] is None

    def test_primary_email_empty_is_none_and_flat_company_name_takes_precedence(self):
        mapped = map_contact(
            {
                "id": 9,
                "email": [{"value": "", "primary": True}, {"value": "fallback@test", "primary": False}],
                "org_name": "Flat Company",
                "org_id": {"name": "Nested Company"},
            }
        )

        assert mapped["primary_email"] is None
        assert mapped["company_name"] == "Flat Company"

    def test_falls_back_to_nested_company_name_and_normalizes_optional_values(self):
        mapped = map_contact(
            {
                "id": None,
                "first_name": "",
                "last_name": None,
                "job_title": "",
                "org_name": "  ",
                "org_id": {"name": "  Example Org  "},
                "email": None,
            }
        )

        assert mapped == {
            "provider_id": "pipedrive",
            "external_id": None,
            "full_name": "",
            "primary_email": None,
            "job_title": None,
            "company_name": "Example Org",
            "custom_fields": {},
        }

    def test_missing_or_malformed_fields_never_raise(self):
        for malformed in (
            None,
            "not-a-record",
            [],
            {
                "id": {"unexpected": "object"},
                "name": 123,
                "first_name": None,
                "last_name": object(),
                "email": [None, "bad entry", {"value": 10, "primary": True}],
                "job_title": None,
                "org_name": [],
                "org_id": "not-an-organization-object",
                "success": False,
                "data": {"not": "a person field"},
                "additional_data": {"pagination": {}},
                "phone": "discarded",
            },
        ):
            result = map_contact(malformed)
            assert set(result) == {
                "provider_id",
                "external_id",
                "full_name",
                "primary_email",
                "job_title",
                "company_name",
                "custom_fields",
            }
            assert result["provider_id"] == "pipedrive"
            assert result["full_name"] == ""
            assert result["primary_email"] is None
            assert result["job_title"] is None
            assert result["company_name"] is None
            assert "phone" not in result["custom_fields"]
            assert "success" not in result["custom_fields"]
            assert "data" not in result["custom_fields"]
            assert "additional_data" not in result["custom_fields"]

    def test_empty_email_list_and_missing_id_map_to_none(self):
        mapped = map_contact({"email": [], "job_title": "   "})

        assert mapped["external_id"] is None
        assert mapped["primary_email"] is None
        # Job-title values are preserved unless absent or literally empty.
        assert mapped["job_title"] == "   "
