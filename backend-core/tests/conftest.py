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
# Same class of leak as SCHEDULER_ENABLED: the pulse's API tests (test_agent_pulse)
# assert the pulse is WIRED in the test kernel, so the developer's real
# AGENT_PULSE_ENABLED=false must not reach the test process either. Pin it on.
os.environ["AGENT_PULSE_ENABLED"] = "true"
# Same class: the cognition tests (test_extractor, test_obsidian) assert the
# background auto-learn actually RUNS. The developer's real MEMORY_AUTO_LEARN
# must not reach the test process either.
os.environ["MEMORY_AUTO_LEARN"] = "true"
# Pin the auth bypass off, whatever the developer's .env says. The endpoint
# tests assert that protected routes answer 401 without a token; if the local
# .env opted into the bypass, they would silently start asserting nothing.
os.environ["AUTH_DEV_BYPASS"] = "false"
# Do not preload the speech model. It is half a gigabyte and takes minutes to
# load on CPU; the kernel does it at boot so the first spoken word is fast, but
# in a test run it just competes with the tests for the same cores.
os.environ["STT_WARM_ON_BOOT"] = "false"
# Point Ollama at a port nothing listens on. Tests that assert real generation
# quality belong against a live model in a manual run, not in the suite — a
# machine that happens to have Ollama up (the owner's) was silently paying for
# real inference on every run (minutes, not seconds) and a request that hung
# could stall the whole suite indefinitely. `brain_offline()` below is for
# tests that want to assert degradation specifically; this is the default for
# everything else, so "the suite passed" means the same thing on every machine.
os.environ["OLLAMA_ENDPOINT"] = "http://127.0.0.1:1"
os.environ["DATABASE_URL"] = f"sqlite:////tmp/sexta_test_{uuid.uuid4().hex}.db"
# Settings.Config.env_file (below) reads the .env file directly via
# pydantic-settings' own DotEnvSettingsSource — a SEPARATE mechanism from the
# main.py `load_dotenv` call this file also neutralizes further down, and one
# the isolation above did nothing to stop. Every AGENT_PULSE_*, BRAIN_MODEL,
# etc. the owner has in their real .env was silently reaching the test
# process regardless of the os.environ overrides here. Point it at a path
# that cannot exist so pydantic-settings finds nothing, same as a machine
# with no .env at all.
os.environ["SEXTA_ENV_FILE"] = "/nonexistent/sexta-feira-os-test-isolation.env"
# The encrypted secrets store must never be touched by tests: main.py calls
# ensure_secrets_loaded() at import, and with OWNER_PASSWORD/DEVICE_PAIRING_CODE
# set above it would otherwise MIGRATE the test values into the developer's real
# repo-root .secrets.enc (which is authoritative over .env once it exists).
# Point it at a temp file; a fresh one per session, discarded with the run.
os.environ["SEXTA_SECRETS_FILE"] = os.path.join(
    os.environ.get("TEMP", "/tmp"), f"sexta_test_secrets_{uuid.uuid4().hex}.enc"
)

# main.py calls load_dotenv(..., override=True) during its own import, which
# clobbers the isolated env vars set above with whatever the developer's real
# .env says — turning every API test into a test against the LIVE dev database
# and the real owner credentials (login 401s, tests write into dev data, CI
# stays green only because it has no .env). Disable .env loading for tests so
# the isolation above is real. The kernel loads .env itself in production.
import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *args, **kwargs: False  # noqa: E731

from app.db.migrations import run_migrations  # noqa: E402

# Bring the schema up so service-level tests (that hit the DB directly, without
# the client fixture) have their tables regardless of execution order.
run_migrations()


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_throttle():
    """The whole suite shares one TestClient, and the login/pair throttle counts
    failures per source IP — every deliberate 401 in a test would otherwise lock
    out 127.0.0.1 for the tests that run after it. Reset before each test."""
    from app.core.rate_limit import throttle

    throttle._failures.clear()
    yield
    throttle._failures.clear()


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
