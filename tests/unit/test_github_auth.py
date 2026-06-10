"""GitHub auth utility tests."""

from unittest.mock import patch

from watchtower.utils.github_auth import resolve_github_token


def test_resolve_github_token_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    assert resolve_github_token() == "env-token"


def test_resolve_github_token_from_keychain(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("keyring.get_password", return_value="keychain-token"):
        assert resolve_github_token() == "keychain-token"


def test_resolve_github_token_missing(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("keyring.get_password", return_value=None):
        assert resolve_github_token() == ""
