import os
import shutil
import tempfile
import pathlib
import pytest
from src.services.ingest import discover_integrations

@pytest.fixture
def temp_integrations_dir():
    # Create a temporary directory for integration discovery
    tmp_dir = tempfile.mkdtemp()
    yield pathlib.Path(tmp_dir)
    shutil.rmtree(tmp_dir)

def test_discover_integrations_valid(temp_integrations_dir, monkeypatch):
    # Set up a valid integration
    pipedrive_dir = temp_integrations_dir / "pipedrive"
    pipedrive_dir.mkdir()
    with open(pipedrive_dir / "__init__.py", "w") as f:
        f.write("def fetch(get_stored): return []")

    # Override the path and the module lookup
    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(temp_integrations_dir))

    # Note: import_module will still try to find 'src.integrations.pipedrive'
    # In a real test environment, we'd mock the importlib.import_module
    # to avoid polluting the real src namespace.
    
    import importlib
    from unittest.mock import MagicMock
    
    mock_module = MagicMock()
    mock_module.fetch = lambda get_stored: []
    
    def mock_import(name):
        if name == "src.integrations.pipedrive":
            return mock_module
        raise ImportError()
        
    monkeypatch.setattr(importlib, "import_module", mock_import)
    
    discovered = discover_integrations()
    assert "pipedrive" in discovered

def test_discover_integrations_ignores_private(temp_integrations_dir, monkeypatch):
    # Set up a directory starting with _
    private_dir = temp_integrations_dir / "_utils"
    private_dir.mkdir()
    with open(private_dir / "__init__.py", "w") as f:
        f.write("def fetch(get_stored): return []")

    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(temp_integrations_dir))
    discovered = discover_integrations()
    assert "_utils" not in discovered

def test_discover_integrations_invalid_contract(temp_integrations_dir, monkeypatch):
    # Missing fetch
    invalid_dir = temp_integrations_dir / "invalid_crm"
    invalid_dir.mkdir()
    with open(invalid_dir / "__init__.py", "w") as f:
        f.write("x = 1")

    monkeypatch.setenv("CRM_INTEGRATIONS_PATH", str(temp_integrations_dir))
    
    import importlib
    from unittest.mock import MagicMock
    mock_module = MagicMock(spec=[]) # No attributes
    monkeypatch.setattr(importlib, "import_module", lambda n: mock_module)

    discovered = discover_integrations()
    assert "invalid_crm" not in discovered