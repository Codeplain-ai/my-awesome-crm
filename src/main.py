import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pythonjsonlogger import jsonlogger

from src.config import settings, load_dotenv
from src.db import engine
from sqlmodel import SQLModel
from src.api import health, contacts, ingest

STATIC_DIR = Path(__file__).parent / "static"

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

    # 0. Load secrets from .env into the environment before anything reads them.
    #    A missing .env is fine; shell / CI environment variables take precedence.
    load_dotenv()

    # 1. Database Migrations (Simulated via create_all for MVP functionality)
    # In a full impl, we would call alembic.command.upgrade(alembic_cfg, "head")
    logger.info("Initializing database schema...")
    SQLModel.metadata.create_all(engine)

    yield

app = FastAPI(title="My Awesome CRM", lifespan=lifespan)

# Routes — the server is unauthenticated. The only credentials in play are the
# per-provider ones each integration reads from the environment when it runs.
app.include_router(health.router)
app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])

@app.get("/", include_in_schema=False)
async def index():
    """Serve the minimal web UI for driving the CRM's endpoints."""
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.CRM_PORT)
