"""Multi-node housekeeping utilities."""

from __future__ import annotations

from watchtower.config.loader import load_watchtower_config
from watchtower.queue.github_issues import GitHubIssuesQueue
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)


def run_housekeeping(stale_hours: int | None = None) -> list[int]:
    """Reclaim stale claims across the fleet."""
    wt = load_watchtower_config()
    hours = stale_hours or int(wt.get("queue", {}).get("stale_claim_hours", 24))
    queue = GitHubIssuesQueue(
        owner=wt["github"]["owner"],
        repo=wt["github"]["repo"],
    )
    reclaimed = queue.release_stale_claims(stale_hours=hours)
    logger.info("Housekeeping reclaimed %d issues", len(reclaimed))
    return reclaimed
