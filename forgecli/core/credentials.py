"""Secure storage for API keys with OS keychain (keyring) and encrypted fallback.

Only the ``get_api_key()`` function is retained — key-write operations
(set/delete/list) were removed alongside the ``forge auth`` and ``forge model``
command groups.
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import json
import sys
import uuid
from pathlib import Path

import keyring
from cryptography.fernet import Fernet

from forgecli.utils.paths import ProjectPaths

KEYRING_SERVICE = "forgecli"


def _get_credentials_file() -> Path:
    paths = ProjectPaths.from_env()
    return paths.config_dir / "credentials.json"


def _get_encryption_key() -> bytes:
    try:
        host_info = f"{uuid.getnode()}:{getpass.getuser()}:{sys.platform}"
    except Exception:
        host_info = "fallback-forgecli-key-salt"
    key_hash = hashlib.sha256(host_info.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_hash)


def _read_encrypted_file() -> dict[str, str]:
    path = _get_credentials_file()
    if not path.exists():
        return {}
    try:
        raw_data = path.read_bytes()
        fernet = Fernet(_get_encryption_key())
        decrypted = fernet.decrypt(raw_data)
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return {}


def get_api_key(provider: str) -> str | None:
    """Retrieve the API key for a provider."""
    provider = provider.lower().strip()
    try:
        val = keyring.get_password(KEYRING_SERVICE, provider)
        if val is not None:
            return val
    except Exception:
        pass
    data = _read_encrypted_file()
    return data.get(provider)
