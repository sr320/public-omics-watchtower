"""GitHub token resolution for CLI and worker processes."""

from __future__ import annotations

import os

DEFAULT_KEYCHAIN_SERVICE = "watchtower-github"


def resolve_github_token(service: str = DEFAULT_KEYCHAIN_SERVICE) -> str:
    """Return GitHub token from GITHUB_TOKEN or macOS Keychain."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token

    try:
        import keyring

        stored = keyring.get_password(service, "GITHUB_TOKEN")
    except Exception:
        return ""

    return stored.strip() if stored else ""
