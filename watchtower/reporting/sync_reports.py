"""Sync local report artifacts to GitHub reports branch."""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path

import requests

GITHUB_API = "https://api.github.com"


def sync_directory(
    owner: str,
    repo: str,
    branch: str,
    source: Path,
    prefix: str,
    token: str,
) -> int:
    """Upload files from source to reports branch via GitHub Contents API."""
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"
    session.headers["Accept"] = "application/vnd.github+json"

    uploaded = 0
    for file_path in source.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(source)
        dest_path = f"{prefix}/{rel}".replace("\\", "/")
        content_b64 = base64.b64encode(file_path.read_bytes()).decode("ascii")

        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{dest_path}"
        get_resp = session.get(url, params={"ref": branch})
        sha = None
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")

        payload = {
            "message": f"watchtower: sync {dest_path}",
            "content": content_b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        put_resp = session.put(url, json=payload, timeout=120)
        if put_resp.status_code in (200, 201):
            uploaded += 1
        else:
            raise RuntimeError(f"Failed to upload {dest_path}: {put_resp.text}")

    return uploaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync reports to GitHub branch")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", default="reports")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--prefix", default="studies")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")

    count = sync_directory(
        args.owner, args.repo, args.branch, args.source, args.prefix, token
    )
    print(f"Uploaded {count} files to {args.branch}")


if __name__ == "__main__":
    main()
