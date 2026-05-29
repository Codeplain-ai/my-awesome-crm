import logging
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from pythonjsonlogger import jsonlogger

from src.config import settings
from src.db import engine
from sqlmodel import SQLModel
from src.api import health, contacts, ingest
from src.auth import verify_api_key

def setup_logging():
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    log_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    root_logger.setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = logging.getLogger("crm.startup")
    
    # 1. Validate Config
    if not settings.CRM_API_KEY:
        logger.error("CRM_API_KEY environment variable is not set")
        raise RuntimeError("CRM_API_KEY environment variable is required")
    
    # 2. Database Migrations (Simulated via create_all for MVP functionality)
    # In a full impl, we would call alembic.command.upgrade(alembic_cfg, "head")
    logger.info("Initializing database schema...")
    SQLModel.metadata.create_all(engine)
    
    yield

app = FastAPI(title="My Awesome CRM", lifespan=lifespan)

# Public routes
app.include_router(health.router)

# Protected routes
protected_deps = [Depends(verify_api_key)]
# Mount protected routes
app.include_router(contacts.router, prefix="/contacts", dependencies=protected_deps, tags=["contacts"])
app.include_router(ingest.router, prefix="/ingest", dependencies=protected_deps, tags=["ingest"])

# Also mount health under /api as per test expectations in test_auth.py
app.include_router(health.router, prefix="/api", dependencies=protected_deps, tags=["protected"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.CRM_PORT)