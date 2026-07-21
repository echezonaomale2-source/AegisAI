"""At-rest encryption for local AegisAI data (personal production use)."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from config.settings import settings
from core.logging_setup import get_logger

log = get_logger("security.encryption")

PREFIX = "enc:v1:"
FILE_PREFIX = b"AEGENC1\0"


class LocalEncryptor:
    """
    Fernet encryption for sensitive local payloads.

    Key source (first match wins):
    1. AEGIS_ENCRYPTION_KEY env / settings.encryption_key
    2. Key file under storage_root / .encryption_key (auto-created)
    """

    def __init__(self, key: bytes | None = None) -> None:
        self._fernet = Fernet(key or self._load_or_create_key())

    @staticmethod
    def _key_path() -> Path:
        root = settings.storage_root
        root.mkdir(parents=True, exist_ok=True)
        return root / ".encryption_key"

    @classmethod
    def _load_or_create_key(cls) -> bytes:
        env_key = (os.environ.get("AEGIS_ENCRYPTION_KEY") or settings.encryption_key or "").strip()
        if env_key:
            raw = env_key.encode("utf-8")
            try:
                Fernet(raw)
                return raw
            except (ValueError, Exception):
                return base64.urlsafe_b64encode(hashlib.sha256(raw).digest())

        path = cls._key_path()
        if path.exists():
            return path.read_bytes().strip()

        key = Fernet.generate_key()
        path.write_bytes(key)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        log.info("created local encryption key at %s", path)
        return key

    def encrypt_text(self, plaintext: str) -> str:
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return PREFIX + token.decode("ascii")

    def decrypt_text(self, maybe_cipher: str) -> str:
        if not maybe_cipher.startswith(PREFIX):
            return maybe_cipher  # plaintext backward compatible
        token = maybe_cipher[len(PREFIX) :].encode("ascii")
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError(
                "Failed to decrypt payload — wrong key or corrupted data"
            ) from exc

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.decrypt(data)

    def encrypt_file_bytes(self, data: bytes) -> bytes:
        """Encrypt binary payloads with a detectable magic prefix (charts, etc.)."""
        return FILE_PREFIX + self.encrypt_bytes(data)

    def decrypt_file_bytes(self, data: bytes) -> bytes:
        if data.startswith(FILE_PREFIX):
            return self.decrypt_bytes(data[len(FILE_PREFIX) :])
        return data  # plaintext backward compatible

    def is_encrypted(self, text: str) -> bool:
        return text.startswith(PREFIX)

    def is_encrypted_file(self, data: bytes) -> bool:
        return data.startswith(FILE_PREFIX)


_encryptor: LocalEncryptor | None = None


def get_encryptor() -> LocalEncryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = LocalEncryptor()
    return _encryptor


def reset_encryptor() -> None:
    global _encryptor
    _encryptor = None
