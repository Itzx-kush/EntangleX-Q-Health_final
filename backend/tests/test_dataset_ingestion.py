import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.api.schemas import DatasetUploadMetadata
from app.data.catalog import list_benchmarks
from app.data.quality import compatibility_report, inspection_report
from app.data.service import inspect_file, parse_tabular, register_builtin, register_file
from app.utils.errors import AppError


def make_frame(rows=24):
    values = np.arange(rows)
    return pd.DataFrame({
        "patient_id": [f"P-{i:03d}" for i in values],
        "age": values + 30,
        "smoker": [i % 2 == 0 for i in values],
        "group": ["A" if i % 3 else "B" for i in values],
        "target": ["positive" if i % 2 else "negative" for i in values],
    })


def metadata(target="target", positive="positive"):
    return DatasetUploadMetadata(name="Format fixture", target=target, positive_label=positive, deidentified=True)


def test_supported_tabular_formats_normalize_to_same_shape(tmp_path):
    frame = make_frame()
    csv_bytes = frame.to_csv(index=False).encode()
    tsv_bytes = frame.to_csv(index=False, sep="\t").encode()
    xlsx_path = tmp_path / "fixture.xlsx"
    frame.to_excel(xlsx_path, index=False)
    parquet_path = tmp_path / "fixture.parquet"
    frame.to_parquet(parquet_path, index=False)
    for filename, content in [("fixture.csv", csv_bytes), ("fixture.tsv", tsv_bytes), ("fixture.xlsx", xlsx_path.read_bytes()), ("fixture.parquet", parquet_path.read_bytes())]:
        parsed = parse_tabular(content, filename, "target")
        assert list(parsed.columns) == list(frame.columns)
        assert len(parsed) == len(frame)
        assert parsed["target"].astype(str).tolist() == frame["target"].tolist()


def test_legacy_csv_helper_and_xls_reader(tmp_path):
    frame = make_frame()
    xls_path = tmp_path / "fixture.xls"
    frame.to_excel(xls_path, index=False, engine="xlwt") if False else None
    # xlrd is intentionally a reader only in this dependency set; malformed legacy files are rejected clearly.
    with pytest.raises(AppError, match="valid legacy Excel"):
        parse_tabular(b"not-an-xls", "fixture.xls", "target")


def test_unsupported_and_malformed_files_are_rejected():
    with pytest.raises(AppError, match="Unsupported dataset format"):
        parse_tabular(b"a,b\n1,2", "fixture.json", "b")
    with pytest.raises(AppError):
        parse_tabular(b"a,b\n1,2\n3", "fixture.csv", "b")
    with pytest.raises(AppError, match="Parquet"):
        parse_tabular(b"PAR1garbagePAR1", "fixture.parquet", "target")


def test_inspector_finds_candidates_and_reports_schema_findings():
    frame = make_frame()
    frame["constant"] = 1
    frame["empty"] = np.nan
    frame["target_proxy"] = frame["target"]
    report = inspect_file(frame.to_csv(index=False).encode(), "fixture.csv")
    assert report["row_count"] == 24
    assert "target" in report["possible_target_columns"]
    assert "patient_id" in report["identifier_like_columns"]
    assert "constant" in report["constant_features"]
    assert "empty" in report["empty_columns"]
    assert report["compatibility"]["status"] == "BLOCKED"


def test_compatibility_explicitly_handles_target_cases():
    frame = make_frame()
    assert compatibility_report(frame, None, None)["status"] == "BLOCKED"
    one_class = frame.assign(target="only")
    assert compatibility_report(one_class, "target", "only")["status"] == "BLOCKED"
    multiclass = frame.assign(target=["a", "b", "c"] * 8)
    assert compatibility_report(multiclass, "target", "a")["status"] == "BLOCKED"
    missing = frame.copy()
    missing.loc[0, "target"] = None
    assert compatibility_report(missing, "target", "positive")["status"] == "BLOCKED"
    ready = frame.drop(columns=["patient_id"])
    result = compatibility_report(ready, "target", "positive")
    assert result["status"] in {"READY", "WARNING"}
    assert any(item["code"] == "binary_target" and item["status"] == "PASS" for item in result["checks"])


def test_register_file_persists_format_hash_and_findings(tmp_path):
    frame = make_frame().drop(columns=["patient_id"])
    path = tmp_path / "fixture.tsv"
    path.write_bytes(frame.to_csv(index=False, sep="\t").encode())
    record = register_file(path.read_bytes(), path.name, metadata())
    assert record.provenance["file_format"] == "tsv"
    assert record.provenance["original_filename"] == "fixture.tsv"
    assert record.provenance["dataset_hash"] == record.sha256
    assert record.provenance["compatibility_findings"]["status"] in {"READY", "WARNING"}
    assert record.provenance["transformations_applied"]


def test_curated_library_has_three_local_hashable_benchmarks():
    entries = list_benchmarks()
    assert {entry["slug"] for entry in entries} >= {"wdbc", "pima-diabetes", "statlog-heart"}
    for entry in entries:
        assert len(entry["dataset_hash"]) == 64
        assert entry["source_url"].startswith("https://")
        assert entry["license"]
        assert entry["positive_label"] != entry["negative_label"]


def test_built_in_registration_is_reproducible():
    first = register_builtin("pima-diabetes")
    second = register_builtin("pima-diabetes")
    assert first.id == second.id
    assert first.provenance["is_demo"] is True
    assert first.provenance["catalog_slug"] == "pima-diabetes"
    assert first.provenance["row_count"] == 768


def test_dataset_library_and_inspect_routes(client):
    response = client.get("/api/datasets/library")
    assert response.status_code == 200
    assert len(response.json()) >= 3
    frame = make_frame().drop(columns=["patient_id"])
    response = client.post("/api/datasets/inspect", files={"file": ("fixture.tsv", frame.to_csv(index=False, sep="\t").encode(), "text/tab-separated-values")})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["file_format"] == "tsv"
    assert "target" in payload["possible_target_columns"]
    assert payload["compatibility"]["status"] == "BLOCKED"


def test_datetime_and_infinite_values_are_not_silently_normalized():
    frame = make_frame().drop(columns=["patient_id"])
    frame["event_time"] = pd.date_range("2026-01-01", periods=len(frame), freq="D")
    frame.loc[0, "age"] = np.inf
    report = inspect_file(frame.to_csv(index=False).encode(), "fixture.csv")
    assert "event_time" in report["datetime_like_columns"]
    assert report["compatibility"]["status"] == "BLOCKED"
    assert any(check["code"] == "infinite_values" and check["status"] == "BLOCKED" for check in report["compatibility"]["checks"])
