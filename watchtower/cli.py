"""Watchtower CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click

from watchtower.config.validator import validate_watchtower_config
from watchtower.db.connection import connect
from watchtower.db.store import Store
from watchtower.queue.github_issues import GitHubIssuesQueue
from watchtower.queue.models import QueueJob
from watchtower.reporting.weekly import generate_weekly_digest, publish_weekly_issue
from watchtower.utils.github_auth import resolve_github_token
from watchtower.utils.logging import setup_logging
from watchtower.utils.paths import find_repo_root
from watchtower.worker.daemon import run_worker


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
@click.pass_context
def main(ctx: click.Context, log_level: str) -> None:
    """Public Omics Watchtower — marine genomics discovery platform."""
    setup_logging(log_level)
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level


@main.group()
def config() -> None:
    """Configuration commands."""


@config.command("validate")
def config_validate() -> None:
    """Validate all YAML configuration files."""
    try:
        configs = validate_watchtower_config()
        click.echo("Configuration valid.")
        click.echo(f"  Species: {list(configs['species'].keys())}")
        click.echo(f"  Phase: {configs['watchtower'].get('phase', 1)}")
    except Exception as exc:  # noqa: BLE001
        raise click.ClickException(str(exc)) from exc


@main.group()
def worker() -> None:
    """Worker node commands."""


@worker.command("run")
@click.option("--node-id", required=True, help="Node identifier")
@click.option("--once", is_flag=True, help="Process at most one job")
@click.option("--max-iterations", type=int, default=None)
def worker_run(node_id: str, once: bool, max_iterations: int | None) -> None:
    """Run worker daemon."""
    run_worker(node_id, once=once, max_iterations=max_iterations)


@worker.command("housekeeping")
@click.option("--node-id", required=True)
def worker_housekeeping(node_id: str) -> None:
    """Reclaim stale job claims."""
    from watchtower.worker.daemon import WorkerDaemon

    daemon = WorkerDaemon(node_id)
    reclaimed = daemon.housekeeping()
    click.echo(f"Reclaimed {len(reclaimed)} stale issues: {reclaimed}")


@main.command("discover")
@click.option("--species", default="crassostrea_gigas")
@click.option("--create-issue/--no-create-issue", default=True)
def discover_cmd(species: str, create_issue: bool) -> None:
    """Run discovery and optionally create a discover job issue."""
    from watchtower.config.loader import load_watchtower_config
    from watchtower.worker.handlers.discover import handle_discover

    wt = load_watchtower_config()
    repo_root = find_repo_root()
    data_root = repo_root / "data"
    data_root.mkdir(exist_ok=True)
    conn = connect(data_root / "watchtower.db")
    store = Store(conn)

    queue = GitHubIssuesQueue(
        owner=wt["github"]["owner"],
        repo=wt["github"]["repo"],
    )

    job = QueueJob(
        job_id=f"discover:{species}:manual",
        job_type="discover",
        species=species,
        payload={"species": [species]},
        created_by="cli@watchtower",
    )

    if create_issue and resolve_github_token():
        issue_num = queue.create_job(job, context_md=f"Manual discovery for {species}")
        job.github_issue_number = issue_num

    handle_discover(job, store, queue)
    datasets = store.list_datasets(limit=20)
    click.echo(f"Discovery complete. {len(datasets)} datasets in database.")
    for d in datasets[:10]:
        click.echo(f"  {d.accession} score={d.relevance_score} status={d.status}")


@main.command("status")
@click.option("--data-root", type=click.Path(path_type=Path), default=None)
def status_cmd(data_root: Path | None) -> None:
    """Show system status summary."""
    root = find_repo_root()
    dr = data_root or root / "data"
    if not (dr / "watchtower.db").exists():
        click.echo("No local database found. Run discover or worker first.")
        return

    conn = connect(dr / "watchtower.db")
    store = Store(conn)

    click.echo("=== Datasets ===")
    for status in ("discovered", "queued", "ready", "completed", "failed", "skipped"):
        rows = store.list_datasets(status=status, limit=1000)
        if rows:
            click.echo(f"  {status}: {len(rows)}")

    click.echo("=== Jobs ===")
    for status in ("queued", "running", "succeeded", "failed"):
        rows = store.list_jobs(status=status, limit=1000)
        if rows:
            click.echo(f"  {status}: {len(rows)}")


@main.command("retry")
@click.argument("job_id")
@click.option("--data-root", type=click.Path(path_type=Path), default=None)
def retry_cmd(job_id: str, data_root: Path | None) -> None:
    """Re-queue a failed job."""
    from watchtower.config.loader import load_watchtower_config

    wt = load_watchtower_config()
    root = find_repo_root()
    dr = data_root or root / "data"
    conn = connect(dr / "watchtower.db")
    store = Store(conn)
    job = store.get_job(job_id)
    if not job:
        raise click.ClickException(f"Job not found: {job_id}")

    payload = json.loads(job.payload_json or "{}")
    queue = GitHubIssuesQueue(
        owner=wt["github"]["owner"],
        repo=wt["github"]["repo"],
    )
    qjob = QueueJob(
        job_id=f"{job_id}:retry",
        job_type=job.job_type,
        dataset_id=job.dataset_id,
        payload=payload,
        species="crassostrea_gigas",
    )
    issue_num = queue.create_job(qjob, context_md=f"Retry of {job_id}")
    click.echo(f"Created retry issue #{issue_num}")


@main.command("report")
@click.option("--weekly/--no-weekly", default=True)
@click.option("--data-root", type=click.Path(path_type=Path), default=None)
@click.option("--publish-issue/--no-publish-issue", default=False)
def report_cmd(weekly: bool, data_root: Path | None, publish_issue: bool) -> None:
    """Generate reports."""
    from watchtower.config.loader import load_watchtower_config

    wt = load_watchtower_config()
    root = find_repo_root()
    dr = data_root or root / "data"
    conn = connect(dr / "watchtower.db")
    store = Store(conn)

    if weekly:
        path = generate_weekly_digest(store, dr / "reports")
        click.echo(f"Weekly digest: {path}")
        if publish_issue and resolve_github_token():
            queue = GitHubIssuesQueue(
                owner=wt["github"]["owner"],
                repo=wt["github"]["repo"],
            )
            issue = publish_weekly_issue(queue, path)
            click.echo(f"Published digest issue #{issue}")


@main.group()
def github() -> None:
    """GitHub integration commands."""


@github.command("store-token")
@click.option("--service", default="watchtower-github")
def store_token(service: str) -> None:
    """Store GitHub token in macOS Keychain."""
    import getpass

    import keyring

    token = getpass.getpass("GitHub token: ")
    keyring.set_password(service, "GITHUB_TOKEN", token)
    click.echo(f"Token stored in keychain service '{service}'")


@github.command("get-token")
@click.option("--service", default="watchtower-github")
def get_token(service: str) -> None:
    """Load token from keychain into GITHUB_TOKEN env hint."""
    import keyring

    token = keyring.get_password(service, "GITHUB_TOKEN")
    if token:
        click.echo(f"Token found in keychain service '{service}'.")
        click.echo("Watchtower loads it automatically; no export required.")
    else:
        click.echo("No token found. Run: watchtower github store-token")


if __name__ == "__main__":
    main()
