"""Secure storage for API keys with OS keychain (keyring) and encrypted fallback."""



from __future__ import annotations

import base64
import contextlib
import getpass
import hashlib
import json
import sys
import uuid
from pathlib import Path

import keyring
from cryptography.fernet import Fernet

from forgecli.utils.paths import ProjectPaths

KEYRING_SERVICE = "forgectx"





def _get_credentials_file() -> Path:

    paths = ProjectPaths.from_env()

    paths.config_dir.mkdir(parents=True, exist_ok=True)

    return paths.config_dir / "credentials.json"





def _get_encryption_key() -> bytes:

    try:

        host_info = f"{uuid.getnode()}:{getpass.getuser()}:{sys.platform}"

    except Exception:

        host_info = "fallback-forgectx-key-salt"

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





def _write_encrypted_file(data: dict[str, str]) -> None:

    path = _get_credentials_file()

    fernet = Fernet(_get_encryption_key())

    encrypted = fernet.encrypt(json.dumps(data).encode("utf-8"))

    path.write_bytes(encrypted)

    with contextlib.suppress(OSError):

        path.chmod(0o600)





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





def set_api_key(provider: str, api_key: str) -> None:

    """Store an API key in the OS keychain, falling back to encrypted disk storage."""

    provider = provider.lower().strip()

    api_key = api_key.strip()

    if not provider or not api_key:

        raise ValueError("provider and api_key are required")

    try:

        keyring.set_password(KEYRING_SERVICE, provider, api_key)

        return

    except Exception:

        data = _read_encrypted_file()

        data[provider] = api_key

        _write_encrypted_file(data)





def delete_api_key(provider: str) -> None:

    """Remove a stored API key."""

    provider = provider.lower().strip()

    with contextlib.suppress(Exception):

        keyring.delete_password(KEYRING_SERVICE, provider)

    data = _read_encrypted_file()

    if provider in data:

        del data[provider]

        _write_encrypted_file(data)





def list_stored_providers() -> list[str]:

    """Return provider names with stored credentials."""

    providers = set(_read_encrypted_file())

    for name in (

        "openai",

        "anthropic",

        "google",

        "openrouter",

        "groq",

        "together",

    ):

        try:

            if keyring.get_password(KEYRING_SERVICE, name):

                providers.add(name)

        except Exception:

            continue

    return sorted(providers)

