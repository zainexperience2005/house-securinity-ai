"""Unit tests for modular FastAPI routers in src/api/routers.

Tests cases, models, reports, bylaws, and thread management endpoints.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app.app)


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "House Scrutiny AI Agent API"
    assert "endpoints" in data
    assert data["endpoints"]["threads"] == "/api/v1/threads"
    assert data["endpoints"]["models"] == "/api/v1/models"


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "openai_model" in data


def test_bylaws_listing(client):
    res = client.get("/api/v1/bylaws")
    assert res.status_code == 200
    data = res.json()
    assert "authorities" in data
    assert "database" in data


def test_authority_bylaw_detail(client):
    res = client.get("/api/v1/bylaws/DHA_Lahore?marla=10")
    assert res.status_code == 200
    data = res.json()
    assert data["authority"] == "DHA_Lahore"
    assert "rules" in data


def test_models_catalog(client):
    res = client.get("/api/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "active_system_model" in data


def test_model_providers(client):
    res = client.get("/api/v1/models/providers")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


def test_cases_listing(client):
    res = client.get("/api/v1/cases?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "count" in data
    assert "cases" in data


def test_threads_listing(client):
    res = client.get("/api/v1/threads?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "count" in data
    assert "threads" in data


def test_case_detail(client):
    res = client.get("/api/v1/cases/case-test-123")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "case-test-123"
    assert "authority" in data


def test_nonexistent_thread_404(client):
    res = client.get("/api/v1/threads/nonexistent-thread-uuid-9999")
    assert res.status_code == 404
