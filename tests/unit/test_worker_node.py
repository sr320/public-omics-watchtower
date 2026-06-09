"""Worker node manager tests."""

import json
from pathlib import Path
from unittest.mock import patch

from watchtower.db.connection import connect
from watchtower.db.store import Store
from watchtower.worker.node import NodeManager


def test_node_capabilities() -> None:
    with patch.object(NodeManager, "__init__", lambda self, node_id, store: None):
        nm = NodeManager("x", None)  # type: ignore[arg-type]
        nm.node_id = "oyster-mini-01"
        nm.config = {
            "data_root": "/tmp",
            "capabilities": {
                "job_types": ["discover", "download"],
                "max_concurrent_jobs": 2,
                "preferred_species": ["crassostrea_gigas"],
            },
        }
        nm.store = None
        assert nm.can_handle("discover", "crassostrea_gigas")
        assert not nm.can_handle("analyze")


def test_node_register(tmp_path: Path) -> None:
    store = Store(connect(tmp_path / "t.db"))
    with patch("watchtower.worker.node.load_node_config") as mock_cfg:
        mock_cfg.return_value = {
            "node_id": "test-mini",
            "hostname": "test.local",
            "data_root": str(tmp_path),
            "capabilities": {"job_types": ["discover"], "max_concurrent_jobs": 1},
        }
        nm = NodeManager("test-mini", store)
        nm.register()
        node = store.get_node("test-mini")
        assert node is not None
        caps = json.loads(node.capabilities_json or "{}")
        assert "discover" in caps["job_types"]
