from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from src.db import get_session
from src.services.ingest import discover_integrations, run_integration_service

router = APIRouter()

@router.post("/discover")
async def trigger_discovery():
    """
    Triggers the discovery of integration plug-ins and returns their names.
    """
    integrations = discover_integrations()
    return {"discovered": integrations}

@router.get("/{integration}")
async def run_integration(
    integration: str, 
    session: Session = Depends(get_session)
):
    """
    Runs the named integration and persists its results.
    """
    try:
        results = run_integration_service(session, integration)
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))