"""Worker node registration and resource checks."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from watchtower.config.loader import load_node_config
from watchtower.db.models import Node
from watchtower.db.store import Store
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)


class NodeManager:
    """Manage node identity, heartbeat, and resource checks."""

    @staticmethod
    def _data_root_for(node_id: str) -> Path:
        cfg = load_node_config(node_id)
        return Path(cfg["data_root"])

    def __init__(self, node_id: str, store: Store) -> None:
        self.node_id = node_id
        self.config = load_node_config(node_id)
        self.store = store
        self.data_root = Path(self.config["data_root"])

    @property
    def capabilities(self) -> dict:
        return self.config.get("capabilities", {})

    @property
    def job_types(self) -> list[str]:
        return self.capabilities.get("job_types", [])

    @property
    def max_concurrent_jobs(self) -> int:
        return int(self.capabilities.get("max_concurrent_jobs", 1))

    @property
    def preferred_species(self) -> list[str]:
        return self.capabilities.get("preferred_species", [])

    def register(self) -> None:
        node = Node(
            node_id=self.node_id,
            hostname=self.config.get("hostname"),
            capabilities_json=json.dumps(self.capabilities),
            status="active",
        )
        self.store.upsert_node(node)
        logger.info("Registered node %s", self.node_id)

    def heartbeat(self) -> None:
        node = Node(
            node_id=self.node_id,
            hostname=self.config.get("hostname"),
            capabilities_json=json.dumps(self.capabilities),
            status="active",
        )
        self.store.upsert_node(node)

    def has_capacity(self) -> bool:
        running = self.store.count_running_jobs(self.node_id)
        return running < self.max_concurrent_jobs

    def has_storage(self) -> bool:
        min_gb = float(self.capabilities.get("storage_gb_free_min", 50))
        try:
            usage = shutil.disk_usage(self.data_root)
            free_gb = usage.free / (1024 ** 3)
            if free_gb < min_gb:
                logger.warning(
                    "Low disk space on %s: %.1f GB free (min %.1f)",
                    self.data_root,
                    free_gb,
                    min_gb,
                )
                return False
        except OSError:
            logger.warning("Cannot check disk usage for %s", self.data_root)
        return True

    def can_handle(self, job_type: str, species: str | None = None) -> bool:
        if job_type not in self.job_types:
            return False
        if species and self.preferred_species and species not in self.preferred_species:
            return False
        return True

    def db_path(self) -> Path:
        return self.data_root / "watchtower.db"

    def logs_dir(self) -> Path:
        path = self.data_root / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
