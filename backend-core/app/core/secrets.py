"""
secrets.py — where the master secrets actually live.

The .env is plaintext on disk; anyone who can read the machine can read it.
This module moves the four master credentials (JWT_SECRET_KEY, VAULT_KEY,
OWNER_PASSWORD, DEVICE_PAIRING_CODE) out of .env into a small file encrypted
with Windows DPAPI (CryptProtectData) — bound to THIS user + THIS machine, so
the ciphertext is useless on any other machine or account. The .env keeps only
non-secret configuration.

Boot flow (called from main.py, right after load_dotenv, BEFORE Settings is
built — see the comment there):

    ensure_secrets_loaded()
      1. store exists  -> read it, inject the values into os.environ so
         pydantic Settings picks them up exactly as if they were in .env;
      2. no store, but .env still carries the secrets (first run after the
         upgrade) -> migrate them INTO the store, then tell the owner once
         which lines to delete from .env;
      3. non-Windows fallback -> plaintext file with owner-only perms plus a
         loud warning (strictly better than .env: one file, no churn).

The store path is overridable via SEXTA_SECRETS_FILE so tests can point it at
a temp file and never touch the real one.
"""
from __future__ import annotations

import ctypes
import json
import logging
import os
import stat
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger("sexta-feira.secrets")

# Master credentials — never supposed to sit plaintext in .env.
SECRET_NAMES = (
    "JWT_SECRET_KEY",
    "VAULT_KEY",
    "OWNER_PASSWORD",
    "DEVICE_PAIRING_CODE",
)

_STORE_FILENAME = ".secrets.enc"
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


def store_path() -> Path:
    """Where the encrypted store lives (overridable for tests)."""
    override = os.environ.get("SEXTA_SECRETS_FILE", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / _STORE_FILENAME


# ── Windows DPAPI (zero dependencies, via ctypes) ────────────────────────────


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _make_blob(data: bytes) -> tuple[_DATA_BLOB, object]:
    buf = ctypes.create_string_buffer(data, len(data))
    blob = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    return blob, buf  # keep the buffer alive across the API call


def _blob_bytes(blob: _DATA_BLOB) -> bytes:
    if not blob.pbData or not blob.cbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _protect(data: bytes) -> bytes:
    """DPAPI-encrypt `data`, bound to the current Windows user + machine."""
    if os.name != "nt":
        raise OSError("DPAPI indisponível fora do Windows")
    crypt32 = ctypes.windll.crypt32
    in_blob, keep = _make_blob(data)
    out_blob = _DATA_BLOB()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None,
        _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out_blob),
    )
    del keep
    if not ok:
        raise ctypes.WinError()
    try:
        return _blob_bytes(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _unprotect(blob: bytes) -> bytes:
    """Decrypt a DPAPI blob created on this same user + machine."""
    if os.name != "nt":
        raise OSError("DPAPI indisponível fora do Windows")
    crypt32 = ctypes.windll.crypt32
    in_blob, keep = _make_blob(blob)
    out_blob = _DATA_BLOB()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None,
        _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out_blob),
    )
    del keep
    if not ok:
        raise ctypes.WinError()
    try:
        return _blob_bytes(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


# ── The store ────────────────────────────────────────────────────────────────


class SecretStore:
    """JSON of name -> secret, encrypted at rest. Loaded once per process."""

    def __init__(
        self,
        path: Path,
        protect: Callable[[bytes], bytes] = _protect,
        unprotect: Callable[[bytes], bytes] = _unprotect,
    ):
        self.path = path
        self._protect = protect
        self._unprotect = unprotect
        self._data: dict[str, str] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            return
        raw = self.path.read_bytes()
        if not raw:
            return
        try:
            decoded = json.loads(self._unprotect(raw).decode("utf-8"))
            if isinstance(decoded, dict):
                self._data = {str(k): str(v) for k, v in decoded.items() if v}
        except Exception as e:  # noqa: BLE001 — a bad store must not brick the boot
            logger.warning(
                "Não consegui decifrar %s (%s). Os segredos serão lidos do ambiente.",
                self.path, e,
            )

    def get(self, name: str) -> str | None:
        self.load()
        return self._data.get(name)

    def set(self, name: str, value: str) -> None:
        self.load()
        self._data[name] = value
        self._persist()

    def _persist(self) -> None:
        try:
            payload = json.dumps(self._data, ensure_ascii=False, sort_keys=True).encode("utf-8")
            encrypted = self._protect(payload)
        except Exception as e:  # noqa: BLE001 — CI/Linux has no DPAPI; degrade loudly
            logger.warning("Não consegui gravar o cofre de segredos (%s).", e)
            return
        try:
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_bytes(encrypted)
            if os.name != "nt":
                os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # owner-only on POSIX
            tmp.replace(self.path)
        except OSError as e:
            logger.warning("Não consegui gravar %s (%s).", self.path, e)


# ── bootstrap ────────────────────────────────────────────────────────────────

_store: SecretStore | None = None


def ensure_secrets_loaded(store: SecretStore | None = None) -> SecretStore:
    """Feed os.environ from the encrypted store; migrate plaintext .env once.

    Returns the store (tests inspect/monkeypatch it).
    """
    s = store or _get_store()
    s.load()
    migrated = False
    for name in SECRET_NAMES:
        current = os.environ.get(name, "")
        stored = s.get(name)
        if not current and stored:
            # .env was cleaned; the store is the source of truth.
            os.environ[name] = stored
        elif current and not stored:
            # First run after the upgrade: .env still carries the secret.
            s.set(name, current)
            migrated = True
        elif current and stored and current != stored:
            # The store is authoritative; a stale .env copy is ignored loudly,
            # so a rotated key that never reached the store cannot silently win.
            os.environ[name] = stored
            logger.warning(
                "%s difere entre o cofre e o ambiente; usando o valor do cofre.", name,
            )
    if migrated:
        logger.warning(
            "Segredos migrados para o cofre criptografado (%s). "
            "Agora você pode remover JWT_SECRET_KEY, VAULT_KEY, OWNER_PASSWORD e "
            "DEVICE_PAIRING_CODE do .env — eles não ficam mais em texto puro.",
            s.path,
        )
    return s


def _get_store() -> SecretStore:
    global _store
    if _store is None:
        _store = SecretStore(store_path())
    return _store
