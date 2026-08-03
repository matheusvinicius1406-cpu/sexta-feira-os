"""
Shared test setup for the private local kernel.

One env, one app, one lifespan for the whole test session. The kernel is a
singleton whose async clients (the brain) and background loops (the Teia's tick)
are torn down on shutdown, so every test module MUST share a single TestClient —
otherwise the first module to tear down would close the shared clients out from
under the others. Hence session scope.
"""
import contextlib
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
# Pin the auth bypass off, whatever the developer's .env says. The endpoint
# tests assert that protected routes answer 401 without a token; if the local
# .env opted into the bypass, they would silently start asserting nothing.
os.environ["AUTH_DEV_BYPASS"] = "false"
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


@contextlib.contextmanager
def brain_offline():
    """Make the local brain unreachable, deterministically.

    Several tests assert that the kernel DEGRADES when Ollama is down. They used
    to get that for free by assuming CI has no Ollama — which means on a machine
    that does run one (the owner's), they failed for a reason that had nothing to
    do with the code. A test whose result depends on whether a service happens to
    be up is a coin flip, not a test.

    The cut is made at the transport, not at `chat`: every brain method goes
    through the same httpx client, so failing it reproduces a real outage across
    chat, embeddings, health and tool-calling at once, instead of one method
    pretending while the others still answer.
    """
    import httpx

    from app.core.di import get_kernel

    brain = get_kernel().brain
    client = brain._client
    original_post, original_get = client.post, client.get

    async def refuse(*args, **kwargs):
        raise httpx.ConnectError("Ollama offline (stub de teste)")

    client.post = refuse
    client.get = refuse
    try:
        yield
    finally:
        client.post, client.get = original_post, original_get
