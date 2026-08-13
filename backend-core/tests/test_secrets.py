"""
The encrypted secrets store (app/core/secrets.py).

DPAPI itself cannot run on CI/Linux, so the ciphers are injected — the tests
cover the store's contract: encrypted at rest, source of truth over .env,
one-time migration of plaintext values, and never bricking the boot on a
corrupt file.
"""
import base64
import os

import pytest

from app.core.secrets import SECRET_NAMES, SecretStore, ensure_secrets_loaded


def _fake_protect(data: bytes) -> bytes:
    return b"enc:" + base64.b64encode(data)


def _fake_unprotect(data: bytes) -> bytes:
    return base64.b64decode(data[4:])


def _make_store(path):
    return SecretStore(path, protect=_fake_protect, unprotect=_fake_unprotect)


def test_store_encrypts_at_rest(tmp_path):
    store = _make_store(tmp_path / "s.enc")
    store.set("JWT_SECRET_KEY", "super-secreto")
    raw = (tmp_path / "s.enc").read_bytes()
    assert b"super-secreto" not in raw          # not plaintext on disk
    assert raw.startswith(b"enc:")               # ciphertext


def test_store_roundtrip(tmp_path):
    store = _make_store(tmp_path / "s.enc")
    store.set("VAULT_KEY", "chave-do-cofre")
    fresh = _make_store(tmp_path / "s.enc")
    assert fresh.get("VAULT_KEY") == "chave-do-cofre"


def test_ensure_secrets_migrates_env_into_store(tmp_path, monkeypatch):
    """First boot after the upgrade: .env still carries the secret -> it moves
    into the store and keeps flowing through os.environ."""
    store = _make_store(tmp_path / "s.enc")
    monkeypatch.setenv("JWT_SECRET_KEY", "valor-plaintext")
    returned = ensure_secrets_loaded(store)
    assert returned is store
    assert store.get("JWT_SECRET_KEY") == "valor-plaintext"
    assert os.environ["JWT_SECRET_KEY"] == "valor-plaintext"
    monkeypatch.delenv("JWT_SECRET_KEY")


def test_store_is_source_of_truth_over_env(tmp_path, monkeypatch):
    store = _make_store(tmp_path / "s.enc")
    store.set("JWT_SECRET_KEY", "valor-do-cofre")
    monkeypatch.setenv("JWT_SECRET_KEY", "valor-antigo-do-env")
    ensure_secrets_loaded(store)
    # The stale .env copy must NOT win — the store is authoritative.
    assert os.environ["JWT_SECRET_KEY"] == "valor-do-cofre"
    monkeypatch.delenv("JWT_SECRET_KEY")


def test_corrupt_store_does_not_brick_boot(tmp_path, caplog):
    p = tmp_path / "s.enc"
    p.write_bytes(b"lixo-que-nao-e-criptografia")
    store = _make_store(p)
    store.load()  # must not raise
    assert store.get("JWT_SECRET_KEY") is None


def test_secret_names_cover_the_master_four():
    assert set(SECRET_NAMES) == {
        "JWT_SECRET_KEY", "VAULT_KEY", "OWNER_PASSWORD", "DEVICE_PAIRING_CODE",
    }


@pytest.mark.parametrize("name", SECRET_NAMES)
def test_each_secret_name_is_string(name):
    assert isinstance(name, str) and name
