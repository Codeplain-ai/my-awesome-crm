import src.integrations.sugarcrm as sugar_pkg

def test_package_exports_only_fetch_contacts():
    """
    Ensures the integration package follows the strict export contract.
    """
    # Check __all__
    assert sugar_pkg.__all__ == ["fetch_contacts"]
    
    # Check that fetch_contacts is available
    assert hasattr(sugar_pkg, "fetch_contacts")
    assert callable(sugar_pkg.fetch_contacts)
    
    # Check that mapping is not leaked in __all__
    assert "map_contact" not in sugar_pkg.__all__
    assert "mapping" not in sugar_pkg.__all__

def test_fetch_contacts_is_discoverable():
    """
    Checks that the attribute exists on the module directly, 
    as required by the importlib-based discovery in ingest.py.
    """
    from src.integrations.sugarcrm import fetch_contacts
    assert fetch_contacts.__name__ == "fetch_contacts"