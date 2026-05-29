import importlib
import logging
import os
import pathlib
from typing import List, Callable, Any

logger = logging.getLogger(__name__)

def get_integrations_base_path() -> pathlib.Path:
    """
    Returns the path to the integrations directory.
    Supports override via CRM_INTEGRATIONS_PATH for testing.
    """
    env_path = os.environ.get("CRM_INTEGRATIONS_PATH")
    if env_path:
        return pathlib.Path(env_path)
    
    # Default to src/integrations/ relative to this file
    return pathlib.Path(__file__).parent.parent / "integrations"

def discover_integrations() -> List[str]:
    """
    Scans the integrations directory and returns identifiers of valid integrations.
    A valid integration is a directory (not starting with _) containing an __init__.py
    and exporting a 'fetch_contacts' callable.
    """
    base_path = get_integrations_base_path()
    discovered = []

    if not base_path.exists() or not base_path.is_dir():
        logger.warning(f"Integrations directory not found at {base_path}")
        return []

    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            # Check for __init__.py to ensure it's a package
            if not (item / "__init__.py").exists():
                continue
            
            try:
                # Construct module path. 
                # If using the default path, it's src.integrations.<name>
                # If using override, we might need to handle sys.path
                module_name = f"src.integrations.{item.name}"
                
                # If overridden, we need to ensure the parent is in sys.path
                # but for standard src/ layout, src is usually the root.
                module = importlib.import_module(module_name)
                
                # Check for contract: fetch_contacts callable
                fetch_fn = getattr(module, "fetch_contacts", None)
                if fetch_fn and callable(fetch_fn):
                    discovered.append(item.name)
                    logger.info(f"Discovered integration: {item.name}")
                else:
                    logger.warning(f"Integration '{item.name}' missing 'fetch_contacts' callable")
            
            except Exception as e:
                logger.error(
                    f"Failed to import integration '{item.name}'", 
                    extra={"error": str(e)}
                )
                
    return discovered