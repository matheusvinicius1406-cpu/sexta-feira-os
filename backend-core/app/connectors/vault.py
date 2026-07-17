"""
Vault — symmetric encryption for owner secrets (API keys/tokens).

Secrets never touch the DB in plaintext. Uses Fernet (AES-128-CBC + HMAC). The
key comes from VAULT_KEY; if unset, an ephemeral key is minted per boot (secrets
won't survive a restart — fine for dev, set VAULT_KEY for real use).
"""
from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger("sexta-feira.vault")


class Vault:
    def __init__(self, key: str | None = None):
        key = key if key is not None else settings.vault_key
        if key:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            ephemeral = Fernet.generate_key()
            logger.warning(
                "VAULT_KEY not set — using an ephemeral key. Secrets will NOT survive "
                "a restart. Set VAULT_KEY in .env for persistent secrets."
            )
            self._fernet = Fernet(ephemeral)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as e:
            # Wrong/rotated key: don't leak, fail closed.
            raise ValueError("Não foi possível descriptografar o segredo (VAULT_KEY mudou?).") from e
