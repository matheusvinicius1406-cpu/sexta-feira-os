"""
Shared test setup for the private local kernel.

One env, one app, one lifespan for the whole test session. The kernel is a
singleton whose async clients (brain, n8n) are closed on shutdown, so every test
module MUST share a single TestClient — otherwise the first module to tear down
would close the shared clients out from under the others. Hence session scope.
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Configure an isolated, ephemeral kernel BEFORE importing the app.
# Force test env vars (overrides any .env / system env for test isolation).
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["OWNER_EMAIL"] = "owner@test.local"
os.environ["OWNER_NAME"] = "Test Owner"
os.environ["OWNER_PASSWORD"] = "a-strong-test-password"
os.environ["DEVICE_PAIRING_CODE"] = "pair-code-123"
os.environ["SCHEDULER_ENABLED"] = "false"  # tests drive run_due() directly
os.environ["DATABASE_URL"] = f"sqlite:////tmp/sexta_test_{uuid.uuid4().hex}.db"

from app.db.migrations import run_migrations  # noqa: E402

# Bring the schema up so service-level tests (that hit the DB directly, without
# the client fixture) have their tables regardless of execution order.
run_migrations()


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def owner_headers(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": os.environ["OWNER_EMAIL"], "password": os.environ["OWNER_PASSWORD"]},
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
