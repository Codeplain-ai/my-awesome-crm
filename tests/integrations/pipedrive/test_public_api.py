"""Public package API tests for the Pipedrive integration."""

from src.integrations import pipedrive


def test_fetch_is_exported_as_package_level_callable():
    """The host must be able to invoke fetch via the integration package."""
    assert callable(pipedrive.fetch)
    assert "fetch" in pipedrive.__all__
