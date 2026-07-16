"""
End-to-end tests for the private local kernel.

These run without Ollama: chat degrades gracefully to 503, and memory is
stored without an embedding. They prove the auth + memory + device + privacy
surface actually works. Run with:  pytest -q
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Configure an isolated, ephemeral kernel BEFORE importing the app.
os.environ.update(
    ENVIRONMENT="development",
    LOG_LEVEL="CRITICAL",
    OWNER_EMAIL="owner@test.local",
    OWNER_NAME="Test Owner",
    OWNER_PASSWORD="a-strong-test-password",
    DEVICE_PAIRING_CODE="pair-code-123",
    DATABASE_URL=f"sqlite:////tmp/sexta_test_{uuid.uuid4().hex}.db",
)

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def owner_headers(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "owner@test.local", "password": "a-strong-test-password"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert "brain_online" in body


def test_chat_requires_auth(client):
    assert client.post("/api/v1/chat", json={"message": "oi"}).status_code == 403


def test_login_rejects_wrong_password(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "owner@test.local", "password": "wrong"})
    assert r.status_code == 401


def test_memory_persists(client, owner_headers):
    r = client.post("/api/v1/memory",
                    json={"content": "Gosto de café forte", "kind": "preference"},
                    headers=owner_headers)
    assert r.status_code == 200
    listing = client.get("/api/v1/memory", headers=owner_headers).json()
    assert any("café forte" in m["content"] for m in listing)


def test_device_pairing_and_access(client):
    r = client.post("/api/v1/auth/devices/pair",
                    json={"pairing_code": "pair-code-123",
                          "device_name": "Pixel", "device_kind": "phone"})
    assert r.status_code == 200
    dtoken = r.json()["device_token"]
    # A paired device acts on behalf of the owner.
    r2 = client.get("/api/v1/memory", headers={"Authorization": f"Bearer {dtoken}"})
    assert r2.status_code == 200


def test_bad_pairing_code_rejected(client):
    r = client.post("/api/v1/auth/devices/pair",
                    json={"pairing_code": "nope", "device_name": "x"})
    assert r.status_code == 401


def test_chat_degrades_gracefully_without_brain(client, owner_headers):
    # Ollama isn't running in CI => a clean 503, not a crash.
    r = client.post("/api/v1/chat", json={"message": "oi"}, headers=owner_headers)
    assert r.status_code == 503
