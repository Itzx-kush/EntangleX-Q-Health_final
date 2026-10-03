"""Environment and database isolation for Scientific CI.

Scientific CI must never touch a developer's runtime directory, a production
database, or real biomedical data.  Everything runs against a throw-away
storage root with synthetic fixtures and no required secrets.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent

# Environment variables that must be neutral during verification.
_SAFE_DEFAULTS = {
    "QHEALTH_DEPLOYMENT_MODE": "local",
    "QHEALTH_API_TOKEN": "",
    "QHEALTH_GROQ_API_KEY": "",
    "QHEALTH_LOG_LEVEL": "WARNING",
}

_prepared = False
_isolated_root: Path | None = None


def isolated_root() -> Path:
    """Return (and create) the throw-away storage root used by verification."""
    global _isolated_root
    if _isolated_root is None:
        _isolated_root = Path(tempfile.mkdtemp(prefix="scientific-ci-"))
    return _isolated_root


def prepare_environment() -> Path:
    """Neutralize the environment *before* any application module is imported."""
    global _prepared
    root = Path(os.environ.get("SCIENTIFIC_CI_STORAGE_ROOT") or isolated_root())
    root.mkdir(parents=True, exist_ok=True)
    os.environ["QHEALTH_STORAGE_ROOT"] = str(root)
    for key, value in _SAFE_DEFAULTS.items():
        os.environ.setdefault(key, value)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    _prepared = True
    return root


def cleanup_environment() -> None:
    """Remove the isolated storage root created by this process."""
    if _isolated_root is not None and _isolated_root.exists():
        shutil.rmtree(_isolated_root, ignore_errors=True)


def is_prepared() -> bool:
    return _prepared


def app_workdir() -> Path:
    return BACKEND_ROOT


def subprocess_environment(**overrides: str) -> dict[str, str]:
    """Environment for deployment-style subprocesses (never contains secrets)."""
    environment = {
        **os.environ,
        "PYTHONPATH": str(BACKEND_ROOT),
        "QHEALTH_STORAGE_ROOT": overrides.pop("QHEALTH_STORAGE_ROOT", str(isolated_root() / "subprocess")),
        **_SAFE_DEFAULTS,
        **overrides,
    }
    Path(environment["QHEALTH_STORAGE_ROOT"]).mkdir(parents=True, exist_ok=True)
    return environment


def initialize_database() -> None:
    """Create the isolated schema exactly the way the application does at startup."""
    from app.database import init_db

    init_db()


@contextmanager
def session() -> Iterator[object]:
    """Isolated database session bound to the verification storage root."""
    from app.database import session_scope

    with session_scope() as scope:
        yield scope


def database_is_initialized() -> bool:
    try:
        initialize_database()
    except Exception:
        return False
    return True
