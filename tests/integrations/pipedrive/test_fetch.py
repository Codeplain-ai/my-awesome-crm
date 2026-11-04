from __future__ import annotations

import logging

import pytest
import requests

from src.integrations import pipedrive


class TestCredentials:
    @pytest.mark.parametrize(
        "environment,missing_key",
        [
            ({}, "PIPEDRIVE_API_TOKEN"),
            ({"PIPEDRIVE_API_TOKEN": "token"}, "PIPEDRIVE_COMPANY_DOMAIN"),
            (
                {"PIPEDRIVE_API_TOKEN": " ", "PIPEDRIVE_COMPANY_DOMAIN": "acme"},
                "PIPEDRIVE_API_TOKEN",
            ),
            (
                {"PIPEDRIVE_API_TOKEN": "token", "PIPEDRIVE_COMPANY_DOMAIN": " "},
                "PIPEDRIVE_COMPANY_DOMAIN",
            ),
        ],
    )
    def test_required_environment_variables_are_named(self, monkeypatch, environment, missing_key):
        monkeypatch.delenv("PIPEDRIVE_API_TOKEN", raising=False)
        monkeypatch.delenv("PIPEDRIVE_COMPANY_DOMAIN", raising=False)
        for key, value in environment.items():
            monkeypatch.setenv(key, value)

        with pytest.raises(RuntimeError, match=missing_key):
            pipedrive._get_credentials()

    def test_company_domain_rejects_url_parts(self, monkeypatch):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "secret")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "https://acme.pipedrive.com")

        with pytest.raises(RuntimeError, match="PIPEDRIVE_COMPANY_DOMAIN"):
            pipedrive._get_credentials()

    def test_trims_nonempty_values(self, monkeypatch):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", " token ")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", " acme ")

        assert pipedrive._get_credentials() == ("token", "acme")


class TestRequestPage:
    def test_sends_v1_api_token_and_pinned_page_size(self, monkeypatch):
        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {"success": True, "data": []}

        observed = {}

        def fake_get(url, *, params, timeout):
            observed.update(url=url, params=params, timeout=timeout)
            return Response()

        monkeypatch.setattr(pipedrive.requests, "get", fake_get)
        assert pipedrive._request_page("acme", "secret") == {"success": True, "data": []}
        assert observed == {
            "url": "https://acme.pipedrive.com/v1/persons",
            "params": {"api_token": "secret", "limit": 100},
            "timeout": 30,
        }

        pipedrive._request_page("acme", "secret", 100)
        assert observed["params"] == {"api_token": "secret", "limit": 100, "start": 100}

    def test_http_errors_propagate(self, monkeypatch):
        class Response:
            def raise_for_status(self):
                raise requests.HTTPError("unauthorized")

        monkeypatch.setattr(pipedrive.requests, "get", lambda *args, **kwargs: Response())
        with pytest.raises(requests.HTTPError, match="unauthorized"):
            pipedrive._request_page("acme", "secret")


class TestFetch:
    def test_maps_every_page_to_contact_records(self, monkeypatch):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "secret")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "acme")
        calls = []
        pages = [
            {
                "success": True,
                "data": [
                    {
                        "id": 1,
                        "name": " Ada Lovelace ",
                        "email": [{"value": "ADA@example.test", "primary": True}],
                    }
                ],
                "additional_data": {
                    "pagination": {"more_items_in_collection": True, "next_start": 100}
                },
            },
            {
                "success": True,
                "data": [{"id": 2, "first_name": "Grace", "last_name": "Hopper"}],
                "additional_data": {"pagination": {"more_items_in_collection": False}},
            },
        ]

        def fake_request(domain, token, start=None):
            calls.append((domain, token, start))
            return pages.pop(0)

        monkeypatch.setattr(pipedrive, "_request_page", fake_request)
        result = pipedrive.fetch(lambda data_type: pytest.fail("get_stored must not be called"))

        assert calls == [("acme", "secret", None), ("acme", "secret", 100)]
        assert result == [
            {
                "data_type": "contact",
                "data": {
                    "provider_id": "pipedrive",
                    "external_id": "1",
                    "full_name": "Ada Lovelace",
                    "primary_email": "ada@example.test",
                    "job_title": None,
                    "company_name": None,
                    "custom_fields": {},
                },
            },
            {
                "data_type": "contact",
                "data": {
                    "provider_id": "pipedrive",
                    "external_id": "2",
                    "full_name": "Grace Hopper",
                    "primary_email": None,
                    "job_title": None,
                    "company_name": None,
                    "custom_fields": {},
                },
            },
        ]

    def test_api_failure_aborts_fetch(self, monkeypatch):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "secret")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "acme")
        monkeypatch.setattr(
            pipedrive,
            "_request_page",
            lambda *args: {"success": False, "error": "unauthorized access"},
        )

        with pytest.raises(RuntimeError, match="unauthorized access"):
            pipedrive.fetch(lambda _: [])

    def test_missing_next_offset_fails_instead_of_truncating(self, monkeypatch):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "secret")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "acme")
        monkeypatch.setattr(
            pipedrive,
            "_request_page",
            lambda *args: {
                "success": True,
                "data": [],
                "additional_data": {
                    "pagination": {"more_items_in_collection": True}
                },
            },
        )

        with pytest.raises(RuntimeError, match="next_start"):
            pipedrive.fetch(lambda _: [])

    def test_repeated_pagination_offset_fails(self, monkeypatch):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "secret")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "acme")
        monkeypatch.setattr(
            pipedrive,
            "_request_page",
            lambda *args: {
                "success": True,
                "data": [],
                "additional_data": {
                    "pagination": {"more_items_in_collection": True, "next_start": 100}
                },
            },
        )

        with pytest.raises(RuntimeError, match="repeated start offset"):
            pipedrive.fetch(lambda _: [])

    def test_mapping_value_error_is_logged_and_skipped(self, monkeypatch, caplog):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "secret")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "acme")
        monkeypatch.setattr(
            pipedrive,
            "_request_page",
            lambda *args: {"success": True, "data": [{"id": 77}]},
        )
        monkeypatch.setattr(
            pipedrive,
            "map_contact",
            lambda _: (_ for _ in ()).throw(ValueError("bad record")),
        )

        with caplog.at_level(logging.WARNING, logger="src.integrations.pipedrive"):
            assert pipedrive.fetch(lambda _: []) == []
        assert "77" in caplog.text
        assert "bad record" in caplog.text

    def test_null_data_is_an_empty_batch(self, monkeypatch):
        monkeypatch.setenv("PIPEDRIVE_API_TOKEN", "secret")
        monkeypatch.setenv("PIPEDRIVE_COMPANY_DOMAIN", "acme")
        monkeypatch.setattr(pipedrive, "_request_page", lambda *args: {"success": True, "data": None})

        assert pipedrive.fetch(lambda _: []) == []
