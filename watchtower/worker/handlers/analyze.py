"""Analysis job handler — runs Nextflow pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from watchtower.config.loader import load_pipeline_config, load_species_config
from watchtower.db.models import Artifact, JobEvent, PipelineRun
from watchtower.db.store import Store
from watchtower.download.staging import runs_dir, write_run_manifest
from watchtower.queue.models import QueueJob
from watchtower.utils.logging import get_logger
from watchtower.utils.paths import find_repo_root
from watchtower.worker.node import NodeManager

logger = get_logger(__name__)


def handle_analyze(
    job: QueueJob,
    store: Store,
    node: NodeManager,
) -> dict[str, str]:
    """Execute Nextflow RNA-seq pipeline."""
    pipeline_id = job.payload.get("pipeline", "rnaseq_salmon_deseq2")
    pipeline_cfg = load_pipeline_config(pipeline_id)
    species_cfg = load_species_config(job.species)

    run_id = f"{job.payload.get('accession', 'run')}_{uuid.uuid4().hex[:8]}"
    run_dir = runs_dir(node.data_root, run_id)
    samplesheet = Path(job.payload["samplesheet"])

    ref_manifest = find_repo_root() / species_cfg.get(
        "reference", "references/crassostrea_gigas/manifest.yaml"
    )
    import yaml

    with ref_manifest.open(encoding="utf-8") as fh:
        ref = yaml.safe_load(fh)
    salmon_index = ref.get("salmon_index_path", "")

    params = {
        "samplesheet": str(samplesheet),
        "salmon_index": salmon_index,
        "outdir": str(run_dir / "results"),
        "contrast": pipeline_cfg.get("contrasts", {}).get("default", "treatment_vs_control"),
    }

    nf_main = find_repo_root() / pipeline_cfg["nextflow"]["main"]
    nf_config = find_repo_root() / pipeline_cfg["nextflow"]["config"]
    profile = pipeline_cfg["nextflow"].get("profile", "mac_arm64")

    run = PipelineRun(
        run_id=run_id,
        job_id=job.job_id,
        profile=profile,
        status="running",
        work_dir=str(run_dir),
        params_json=json.dumps(params),
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    store.upsert_pipeline_run(run)

    dataset = store.get_dataset(job.dataset_id or "")
    if dataset:
        dataset.status = "analyzing"
        store.upsert_dataset(dataset)

    write_run_manifest(run_dir, {
        "run_id": run_id,
        "job_id": job.job_id,
        "params": params,
        "pipeline": pipeline_id,
    })

    cmd = [
        "nextflow", "run", str(nf_main),
        "-c", str(nf_config),
        "-profile", profile,
        "-work-dir", str(run_dir / "work"),
        "--samplesheet", params["samplesheet"],
        "--salmon_index", params["salmon_index"],
        "--outdir", params["outdir"],
        "--contrast", params["contrast"],
        "-with-report", str(run_dir / "nextflow_report.html"),
        "-with-trace", str(run_dir / "trace.txt"),
    ]

    # Hard ceiling so a wedged Nextflow run cannot hold the worker slot forever.
    nf_timeout = int(
        os.environ.get(
            "WATCHTOWER_NEXTFLOW_TIMEOUT",
            pipeline_cfg.get("nextflow", {}).get("timeout_sec", 24 * 3600),
        )
    )
    logger.info("Running Nextflow (timeout %ds): %s", nf_timeout, " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(find_repo_root()),
            timeout=nf_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc).isoformat()
        store.upsert_pipeline_run(run)
        raise RuntimeError(
            f"Nextflow run {run_id} timed out after {nf_timeout}s; aborted."
        ) from exc

    if result.returncode != 0:
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc).isoformat()
        store.upsert_pipeline_run(run)
        raise RuntimeError(f"Nextflow failed: {result.stderr[-2000:]}")

    run.status = "succeeded"
    run.finished_at = datetime.now(timezone.utc).isoformat()
    store.upsert_pipeline_run(run)

    artifacts = _register_artifacts(store, run_id, Path(params["outdir"]))
    store.add_job_event(
        JobEvent(
            job_id=job.job_id,
            event_type="analyze_complete",
            message=f"Pipeline run {run_id} succeeded with {len(artifacts)} artifacts",
        )
    )

    if dataset:
        dataset.status = "completed"
        store.upsert_dataset(dataset)

    return {
        "run_id": run_id,
        "outdir": params["outdir"],
        "artifacts": json.dumps(artifacts),
    }


def _register_artifacts(store: Store, run_id: str, outdir: Path) -> list[str]:
    artifact_map = {
        "deg_table": "deg/deseq2_results.csv",
        "pca_plot": "plots/pca.png",
        "volcano_plot": "plots/volcano_*.png",
        "go_enrichment": "enrichment/go_enrichment.csv",
        "study_report": "report/study_report.md",
    }
    registered: list[str] = []
    for artifact_type, pattern in artifact_map.items():
        if "*" in pattern:
            matches = list(outdir.glob(pattern))
            paths = matches
        else:
            p = outdir / pattern
            paths = [p] if p.exists() else []

        for path in paths:
            aid = f"{run_id}:{artifact_type}"
            store.add_artifact(
                Artifact(
                    artifact_id=aid,
                    run_id=run_id,
                    artifact_type=artifact_type,
                    path=str(path),
                )
            )
            registered.append(aid)
    return registered
