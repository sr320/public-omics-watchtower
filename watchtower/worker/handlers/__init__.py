from watchtower.worker.handlers.analyze import handle_analyze
from watchtower.worker.handlers.discover import handle_discover
from watchtower.worker.handlers.download import handle_download
from watchtower.worker.handlers.report import handle_report

__all__ = ["handle_analyze", "handle_discover", "handle_download", "handle_report"]
