"""Deployment-package regression checks for the Render `/app/app` layout."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"


def test_production_sources_do_not_import_backend_app_namespace():
    invalid: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("backend.app"):
                invalid.append(f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("backend.app"):
                        invalid.append(f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}")
    assert invalid == [], f"Render-incompatible production imports: {invalid}"


def test_app_main_imports_from_render_workdir(tmp_path):
    environment = {
        **os.environ,
        "PYTHONPATH": ".",
        "QHEALTH_STORAGE_ROOT": str(tmp_path / "runtime"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.main import app, api; "
                "assert app is not None; "
                "assert len(api.routes) >= 1"
            ),
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr