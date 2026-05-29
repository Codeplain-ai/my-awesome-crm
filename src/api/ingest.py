from fastapi import APIRouter
from src.services.ingest import discover_integrations

router = APIRouter()

@router.post("/discover")
async def trigger_discovery():
    """
    Triggers the discovery of integration plug-ins and returns their names.
    """
    integrations = discover_integrations()
    return {"discovered": integrations}