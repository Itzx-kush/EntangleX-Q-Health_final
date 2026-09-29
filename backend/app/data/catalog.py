"""Immutable, deployment-safe catalog of curated public medical datasets."""
from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from threading import Lock

from ..utils.errors import AppError

_lock = Lock()
_manifest: tuple[dict, ...] | None = None


def _root():
    return files("app.data.builtin_datasets")


def _load_manifest() -> tuple[dict, ...]:
    global _manifest
    with _lock:
        if _manifest is not None:
            return _manifest
        raw = json.loads(_root().joinpath("manifest.json").read_text(encoding="utf-8"))
        required = {
            "slug", "filename", "name", "domain", "source", "source_url", "version",
            "license", "attribution", "target", "target_type", "positive_label",
            "negative_label", "row_count", "feature_count", "class_labels", "sha256",
        }
        seen: set[str] = set()
        checked = []
        for entry in raw:
            if required - set(entry) or entry["slug"] in seen:
                raise AppError("builtin_manifest_invalid", "The built-in dataset manifest is invalid.", 500)
            seen.add(entry["slug"])
            checked.append(dict(entry))
        if len(checked) != 5:
            raise AppError("builtin_manifest_invalid", "Exactly five built-in datasets are required.", 500)
        _manifest = tuple(checked)
        return _manifest


def list_builtin_datasets(*, include_readiness: bool = True) -> list[dict]:
    items = [
        {
            **{key: value for key, value in entry.items() if key != "filename"},
            "origin": "built_in",
            "dataset_status": "available",
        }
        for entry in _load_manifest()
    ]
    if include_readiness:
        from ..demo_readiness import readiness_for
        for item in items:
            item["demo_readiness"] = readiness_for(item["slug"])
    return items


def get_builtin_dataset(slug: str) -> dict:
    entry = next((item for item in _load_manifest() if item["slug"] == slug), None)
    if entry is None:
        raise AppError("builtin_dataset_not_found", "The requested built-in dataset is unavailable.", 404)
    return dict(entry)


def builtin_bytes(slug: str) -> tuple[dict, bytes]:
    entry = get_builtin_dataset(slug)
    try:
        content = _root().joinpath(entry["filename"]).read_bytes()
    except (FileNotFoundError, OSError) as exc:
        raise AppError("builtin_dataset_missing", "A packaged built-in dataset resource is unavailable.", 500) from exc
    if hashlib.sha256(content).hexdigest() != entry["sha256"]:
        raise AppError("builtin_dataset_integrity", "A packaged built-in dataset failed its integrity check.", 500)
    return entry, content