"""Local, deterministic catalog of curated research benchmarks.

Runtime never downloads these sources.  The CSV snapshots live under
``data/benchmarks`` and their source/licence metadata is kept alongside the
catalog so an experiment can be reproduced from the exact stored bytes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..utils.errors import AppError

BENCHMARK_ROOT = Path(__file__).resolve().parents[3] / "data" / "benchmarks"

_CATALOG = (
    {
        "slug": "wdbc",
        "name": "Breast Cancer Wisconsin Diagnostic",
        "domain": "oncology",
        "description": "UCI diagnostic breast-mass measurements for a binary malignant/benign benchmark.",
        "source": "UCI Machine Learning Repository",
        "source_url": "https://doi.org/10.24432/C5DW2B",
        "version": "UCI snapshot; 569 observations",
        "license": "CC BY 4.0",
        "task": "binary_classification",
        "target": "diagnosis",
        "positive_label": "malignant",
        "negative_label": "benign",
        "rows": 569,
        "features": 30,
        "numeric_feature_count": 30,
        "categorical_feature_count": 0,
        "filename": "wdbc.csv",
        "is_demo": True,
    },
    {
        "slug": "pima-diabetes",
        "name": "Pima Indians Diabetes",
        "domain": "endocrinology",
        "description": "UCI diabetes benchmark with measured attributes and a binary outcome label.",
        "source": "UCI Machine Learning Repository",
        "source_url": "https://archive.ics.uci.edu/dataset/529/pima+indians+diabetes",
        "version": "UCI snapshot; 768 observations",
        "license": "CC BY 4.0",
        "task": "binary_classification",
        "target": "outcome",
        "positive_label": "1",
        "negative_label": "0",
        "rows": 768,
        "features": 8,
        "numeric_feature_count": 8,
        "categorical_feature_count": 0,
        "filename": "pima_diabetes.csv",
        "is_demo": True,
    },
    {
        "slug": "statlog-heart",
        "name": "Statlog Heart Disease",
        "domain": "cardiovascular",
        "description": "UCI Statlog heart benchmark with a documented absence/presence binary target.",
        "source": "UCI Machine Learning Repository",
        "source_url": "https://archive.ics.uci.edu/dataset/145/statlog+heart",
        "version": "UCI snapshot; 270 observations",
        "license": "CC BY 4.0",
        "task": "binary_classification",
        "target": "heart_disease",
        "positive_label": "2",
        "negative_label": "1",
        "rows": 270,
        "features": 13,
        "numeric_feature_count": 13,
        "categorical_feature_count": 0,
        "filename": "statlog_heart.csv",
        "is_demo": True,
    },
)


def _entry(raw: dict) -> dict:
    path = BENCHMARK_ROOT / raw["filename"]
    if not path.is_file():
        raise AppError("benchmark_missing", "A curated benchmark asset is unavailable.", 500)
    return {
        **raw,
        "dataset_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "hash_algorithm": "sha256",
        "hash_scope": "exact packaged benchmark bytes",
    }


def list_benchmarks() -> list[dict]:
    return [_entry(dict(item)) for item in _CATALOG]


def get_benchmark(slug: str) -> dict:
    for item in list_benchmarks():
        if item["slug"] == slug:
            return item
    raise AppError("benchmark_not_found", "The requested curated benchmark is not available.", 404)


def benchmark_bytes(slug: str) -> tuple[dict, bytes]:
    entry = get_benchmark(slug)
    return entry, (BENCHMARK_ROOT / entry["filename"]).read_bytes()
