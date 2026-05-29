import os
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db import get_session
from sqlmodel import SQLModel, create_engine, Session

def test_unauthorized_access(monkeypatch):
    monkeypatch.setenv("CRM_API_KEY", "secret-key")
    # Health is public, but /api/health is protected in main.py
    with TestClient(app) as client:
        # No header
        response = client.get("/api/health")
        assert response.status_code == 401
        
        # Wrong header
        response = client.get("/api/health", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

def test_authorized_access(monkeypatch):
    key = "valid-secret"
    monkeypatch.setenv("CRM_API_KEY", key)
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"X-API-Key": key})
        assert response.status_code == 200