"""Path utilities."""

from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from start to find repository root (contains pyproject.toml)."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


def resolve_data_path(data_root: str | Path, *parts: str) -> Path:
    """Build path under data root and ensure parent exists."""
    path = Path(data_root).joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative_path(base: Path, target: Path) -> Path:
    """Return target relative to base; raise if target escapes base."""
    base_resolved = base.resolve()
    target_resolved = target.resolve()
    try:
        return target_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(f"Path {target} escapes data root {base}") from exc
