from __future__ import annotations

import shutil
import time
from typing import Any
from sqlalchemy import text
from ..config import get_settings
from ..database import engine


def probe_database(db_engine=None) -> dict[str, Any]:
    """Lightweight database connectivity and latency probe using SELECT 1.

    Never executes expensive queries or reveals connection paths/passwords.
    """
    target_engine = db_engine or engine
    started = time.perf_counter()
    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            journal = conn.execute(text("PRAGMA journal_mode")).scalar()
            return {
                "available": True,
                "latency_ms": elapsed,
                "journal_mode": str(journal).lower() if journal else "wal",
                "error": None,
            }
    except Exception as exc:
        return {
            "available": False,
            "latency_ms": None,
            "journal_mode": None,
            "error": type(exc).__name__,
        }


def probe_storage(settings=None) -> dict[str, Any]:
    """Safe, read-only diagnostic check for storage availability and capacity.

    Never exposes full filesystem paths or biomedical directories to clients.
    """
    active_settings = settings or get_settings()
    root = active_settings.root

    dirs_available = {}
    for name in ["data", "models", "experiments"]:
        try:
            dirs_available[name] = (root / name).is_dir()
        except OSError:
            dirs_available[name] = False

    all_available = all(dirs_available.values())

    disk_free_bytes = None
    disk_total_bytes = None
    try:
        usage = shutil.disk_usage(root)
        disk_free_bytes = int(usage.free)
        disk_total_bytes = int(usage.total)
    except OSError:
        pass

    return {
        "available": all_available,
        "directories": dirs_available,
        "disk_free_bytes": disk_free_bytes,
        "disk_total_bytes": disk_total_bytes,
    }
