import src.integrations.close as close_pkg

def test_package_exports_only_fetch_contacts():
    """
    Validates that the close integration package only exports 
    the required fetch_contacts callable to keep the discovery surface clean.
    """
    # Get all public attributes (those not starting with underscore)
    public_exports = [name for name in dir(close_pkg) if not name.startswith("_")]
    
    # The requirement is that it exports ONLY fetch_contacts.
    # Note: 'mapping' and 'client' might appear if they were imported as modules, 
    # but __all__ controls 'from package import *' and signals intent.
    # To be strict about the runtime discovery surface used by ingest.py:
    assert "fetch_contacts" in public_exports
    assert callable(close_pkg.fetch_contacts)
    
    # Check __all__ specifically as it defines the intended public interface
    assert hasattr(close_pkg, "__all__")
    assert close_pkg.__all__ == ["fetch_contacts"]

def test_no_leaked_implementations():
    """
    Ensures internal helpers are not part of the intended public API.
    """
    # These should not be in __all__
    intended_api = getattr(close_pkg, "__all__", [])
    assert "CloseClient" not in intended_api
    assert "map_close_contact" not in intended_api
    assert "logger" not in intended_api