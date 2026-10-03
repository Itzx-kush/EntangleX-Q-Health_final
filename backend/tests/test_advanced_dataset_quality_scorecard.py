from __future__ import annotations

import io
from copy import deepcopy
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text

from app.api.schemas import DatasetUploadMetadata, TrainingConfig
from app.audit.service import get_events
from app.data.service import register_csv
from app.data_quality import (
    assess_dataset_quality,
    compare_scorecards,
    compute_assessment_fingerprint,
    export_scorecard_markdown,
    get_latest_scorecard,
    get_scorecard,
    list_scorecards,
    preflight_dataset_quality,
)
from app.data_quality.schemas import DatasetQualityRequest
from app.database import Base, engine, session_scope
from app.main import app
from app.migrations import _repair_dataset_quality_scorecard_schema
from app.protocols.service import create_protocol_version, publish_protocol_version
from app.storage.entities import (
    Artifact,
    Dataset,
    DatasetQualityScorecard,
    DatasetVersion,
    Experiment,
    ScientificAuditEvent,
)
from app.utils.errors import AppError


def _create_clean_dataset(n_rows: int = 100):
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "age": rng.integers(20, 80, size=n_rows),
        "blood_pressure": rng.normal(120, 15, size=n_rows),
        "cholesterol": rng.normal(200, 30, size=n_rows),
        "biomarker_a": rng.normal(5.0, 1.0, size=n_rows),
        "gender": rng.choice(["Male", "Female"], size=n_rows),
        "stage": rng.choice(["I", "II", "III"], size=n_rows),
    })
    # Target with balanced distribution
    score = df["age"] * 0.05 + df["cholesterol"] * 0.01 + rng.normal(0, 1, size=n_rows)
    df["disease_present"] = np.where(score > np.median(score), "positive", "negative")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    meta = DatasetUploadMetadata(
        name="Clean Biomedical Cohort",
        target="disease_present",
        positive_label="positive",
        deidentified=True,
    )
    return register_csv(csv_bytes, "clean_biomedical.csv", meta)


def test_scorecard_schema_and_indexes_exist():
    inspector = inspect(engine)
    assert "dataset_quality_scorecards" in inspector.get_table_names()

    cols = {c["name"] for c in inspector.get_columns("dataset_quality_scorecards")}
    assert "id" in cols
    assert "schema_version" in cols
    assert "dataset_id" in cols
    assert "dataset_version_id" in cols
    assert "status" in cols
    assert "operation_key" in cols
    assert "assessment_fingerprint" in cols
    assert "configuration" in cols
    assert "summary" in cols
    assert "domains" in cols
    assert "schema_snapshot" in cols
    assert "limitations" in cols
    assert "provenance" in cols
    assert "artifact_id" in cols

    indexes = {idx["name"] for idx in inspector.get_indexes("dataset_quality_scorecards")}
    assert "ix_scorecard_dataset_id" in indexes
    assert "ix_scorecard_fingerprint" in indexes
    assert "ix_scorecard_status" in indexes


def test_partial_legacy_scorecard_schema_is_repaired_without_losing_rows(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-quality.sqlite3'}")
    Base.metadata.create_all(legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(text("DROP TABLE dataset_quality_scorecards"))
        connection.execute(text("""
            CREATE TABLE dataset_quality_scorecards (
                id VARCHAR(36) PRIMARY KEY,
                dataset_id VARCHAR(36),
                operation_key VARCHAR(128),
                summary JSON
            )
        """))
        connection.execute(
            text("INSERT INTO dataset_quality_scorecards (id, dataset_id, operation_key, summary) "
                 "VALUES ('legacy-scorecard', 'legacy-dataset', 'legacy-operation', '{}')")
        )
        _repair_dataset_quality_scorecard_schema(connection)

    inspector = inspect(legacy_engine)
    columns = {column["name"] for column in inspector.get_columns("dataset_quality_scorecards")}
    assert {
        "schema_version", "dataset_version_id", "experiment_id", "protocol_version_id",
        "pipeline_version_id", "status", "assessment_fingerprint", "configuration",
        "domains", "schema_snapshot", "limitations", "provenance", "artifact_id",
        "created_at", "completed_at",
    } <= columns
    with legacy_engine.connect() as connection:
        preserved = connection.execute(text(
            "SELECT id, operation_key FROM dataset_quality_scorecards WHERE id = 'legacy-scorecard'"
        )).one()
    assert preserved == ("legacy-scorecard", "legacy-operation")


def test_latest_scorecard_missing_response_has_typed_empty_state_code(client, registered):
    response = client.get(f"/api/datasets/{registered.id}/quality-scorecard/latest")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "quality_scorecard_not_found"
    assert response.json()["error"]["message"] == "No quality scorecard found for this dataset/version."
    assert response.json()["error"]["request_id"]


def test_assess_clean_dataset_quality_passes():
    registered = _create_clean_dataset(n_rows=120)

    with session_scope() as session:
        req = DatasetQualityRequest(
            subgroup_field="gender",
        )
        scorecard = assess_dataset_quality(session, registered.id, req)

        assert scorecard.status == "PASS"
        assert scorecard.summary["overall_status"] == "PASS"
        assert scorecard.summary["failed"] == 0
        assert scorecard.summary["quality_score"] == 100.0
        assert scorecard.summary["total_checks"] >= 20

        # Verify domains exist
        domains = scorecard.domains
        for d in [
            "schema_integrity",
            "completeness",
            "duplicate_integrity",
            "target_integrity",
            "feature_health",
            "class_balance",
            "data_leakage",
            "sensitive_fields",
            "context_compatibility",
        ]:
            assert d in domains
            assert domains[d]["status"] in ("PASS", "NOT_APPLICABLE")

        # Subgroup coverage should pass
        subgroup_check = next(
            c for c in domains["context_compatibility"]["checks"] if c["name"] == "subgroup_coverage"
        )
        assert subgroup_check["status"] == "PASS"

        # Schema snapshot safety: aggregates only, no raw rows
        snapshot = scorecard.schema_snapshot
        assert snapshot["total_rows"] == 120
        assert snapshot["total_features"] == 6
        assert len(snapshot["columns"]) == 7
        for col_prof in snapshot["columns"]:
            assert "name" in col_prof
            assert "null_count" in col_prof
            assert "sample_stats" in col_prof
            assert "raw_values" not in col_prof
            assert "rows" not in col_prof

        # Artifact was registered
        assert scorecard.artifact_id is not None
        art = session.get(Artifact, scorecard.artifact_id)
        assert art is not None
        assert art.artifact_type == "dataset_quality_scorecard"


def test_completeness_and_missingness_checks():
    rng = np.random.default_rng(99)
    # Small sample size (< 30) with heavy missingness
    df = pd.DataFrame({
        "f1": [1.0, 2.0, np.nan, 4.0, np.nan, 6.0, np.nan, 8.0, 9.0, np.nan, 11.0, 12.0],
        "f2": [np.nan] * 12,  # Completely empty column
        "target": ["pos", "neg"] * 6,
    })
    meta = DatasetUploadMetadata(name="Incomplete Data", target="target", positive_label="pos", deidentified=True)
    reg = register_csv(df.to_csv(index=False).encode(), "incomplete.csv", meta)

    with session_scope() as session:
        scorecard = assess_dataset_quality(session, reg.id, DatasetQualityRequest())
        assert scorecard.status in ("WARN", "FAIL")

        completeness = scorecard.domains["completeness"]
        check_names = {c["name"]: c for c in completeness["checks"]}

        # Sample size should fail or warn (< 30 rows)
        assert check_names["sample_size_adequacy"]["status"] == "FAIL"

        # Empty column check should fail
        assert check_names["empty_rows_or_columns"]["status"] == "FAIL"
        assert "f2" in check_names["empty_rows_or_columns"]["details"]["empty_columns"]

        # Quality score should reflect deductions
        assert scorecard.summary["quality_score"] < 70.0


def test_target_integrity_and_zero_variance():
    # Target with missing labels and only 1 class
    df = pd.DataFrame({
        "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0] * 5,
        "single_target": ["only_class"] * 48 + [np.nan, np.nan],
        "valid_target": ["pos", "neg"] * 25,
    })
    meta = DatasetUploadMetadata(name="Bad Target", target="valid_target", positive_label="pos", deidentified=True)
    reg = register_csv(df.to_csv(index=False).encode(), "bad_target.csv", meta)

    with session_scope() as session:
        scorecard = assess_dataset_quality(
            session, reg.id, DatasetQualityRequest(target_column="single_target", positive_label="only_class")
        )
        assert scorecard.status == "FAIL"

        target_dom = scorecard.domains["target_integrity"]
        c_names = {c["name"]: c for c in target_dom["checks"]}

        # Missing target values must FAIL
        assert c_names["target_missingness"]["status"] == "FAIL"
        assert c_names["target_missingness"]["severity"] == "CRITICAL"

        # Single class must FAIL
        assert c_names["target_class_cardinality"]["status"] == "FAIL"
        assert c_names["target_class_cardinality"]["severity"] == "CRITICAL"


def test_data_leakage_and_constant_features():
    n = 60
    # Proxy feature perfectly correlated with target
    target_vals = np.array([0, 1] * 30)
    df = pd.DataFrame({
        "patient_id": [f"PID_{i}" for i in range(n)],  # Identifier among features
        "constant_feature": [42.0] * n,  # Constant feature
        "perfect_leakage": target_vals.astype(float),  # r = 1.0 with target
        "index_counter": np.arange(n, dtype=float),  # Sequential index
        "normal_feat": np.random.default_rng(12).normal(size=n),
        "target": target_vals,
    })
    meta = DatasetUploadMetadata(name="Leakage Dataset", target="target", positive_label="1", deidentified=True)
    reg = register_csv(df.to_csv(index=False).encode(), "leakage.csv", meta)

    with session_scope() as session:
        scorecard = assess_dataset_quality(session, reg.id, DatasetQualityRequest())

        # Constant feature detected
        feat_health = scorecard.domains["feature_health"]
        c_names = {c["name"]: c for c in feat_health["checks"]}
        assert c_names["constant_features"]["status"] == "WARN"
        assert "constant_feature" in c_names["constant_features"]["details"]["constant_columns"]

        # Data leakage detected
        leakage = scorecard.domains["data_leakage"]
        l_names = {c["name"]: c for c in leakage["checks"]}
        assert l_names["target_correlation_leakage"]["status"] == "FAIL"
        assert l_names["target_correlation_leakage"]["severity"] == "CRITICAL"
        assert l_names["identifier_in_features"]["status"] == "WARN"
        assert l_names["index_monotonic_leakage"]["status"] == "WARN"


def test_sensitive_direct_identifiers_detection():
    df = pd.DataFrame({
        "ssn": ["000-00-0000"] * 40,
        "mrn": ["MRN12345"] * 40,
        "age": np.arange(40),
        "target": ["pos", "neg"] * 20,
    })
    meta = DatasetUploadMetadata(name="PII Dataset", target="target", positive_label="pos", deidentified=True)
    reg = register_csv(df.to_csv(index=False).encode(), "pii.csv", meta)

    with session_scope() as session:
        scorecard = assess_dataset_quality(session, reg.id, DatasetQualityRequest())

        sens = scorecard.domains["sensitive_fields"]
        s_names = {c["name"]: c for c in sens["checks"]}
        assert s_names["direct_identifiers_scan"]["status"] == "FAIL"
        assert "ssn" in s_names["direct_identifiers_scan"]["details"]["flagged_columns"]
        assert "mrn" in s_names["direct_identifiers_scan"]["details"]["flagged_columns"]
        assert s_names["deidentification_status"]["status"] == "PASS"


def test_context_compatibility_protocol_and_reference_shift():
    reg = _create_clean_dataset(n_rows=80)

    # 1. Without protocol or reference -> NOT_APPLICABLE
    with session_scope() as session:
        sc1 = assess_dataset_quality(session, reg.id, DatasetQualityRequest())
        compat1 = sc1.domains["context_compatibility"]
        c_map1 = {c["name"]: c for c in compat1["checks"]}
        assert c_map1["protocol_compatibility"]["status"] == "NOT_APPLICABLE"
        assert c_map1["reference_distribution_shift"]["status"] == "NOT_APPLICABLE"
        assert any("protocol" in lim.lower() for lim in sc1.limitations)

    # 2. With protocol version
    from app.protocols.templates import BUILTIN_TEMPLATES
    from app.protocols.schemas import ProtocolCreateRequest, ProtocolDefinitionSpec
    proto_def = deepcopy(BUILTIN_TEMPLATES[0]["definition"])
    proto_def["dataset_policy"]["target_column"] = "disease_present"
    proto_name = f"Quality Evaluation Protocol {uuid4().hex[:6]}"

    with session_scope() as session:
        req_p = ProtocolCreateRequest(
            protocol_name=proto_name,
            description="Protocol for data quality verification",
            definition=ProtocolDefinitionSpec.model_validate(proto_def),
        )
        pv, _ = create_protocol_version(session, req_p)
        pv = publish_protocol_version(session, pv.id)
        pv_id = pv.id

        sc2 = assess_dataset_quality(
            session,
            reg.id,
            DatasetQualityRequest(protocol_version_id=pv_id),
        )
        compat2 = sc2.domains["context_compatibility"]
        c_map2 = {c["name"]: c for c in compat2["checks"]}
        assert c_map2["protocol_compatibility"]["status"] == "PASS"


def test_determinism_and_idempotency():
    reg = _create_clean_dataset(n_rows=70)
    req = DatasetQualityRequest(
        thresholds={"min_row_count": 40},
    )

    with session_scope() as session:
        sc1 = assess_dataset_quality(session, reg.id, req)
        sc1_id = sc1.id
        sc1_fp = sc1.assessment_fingerprint

        # Re-assessment with identical parameters returns existing record
        sc2 = assess_dataset_quality(session, reg.id, req)
        assert sc2.id == sc1_id
        assert sc2.assessment_fingerprint == sc1_fp

        # Fingerprint computation function is deterministic
        context = {
            "experiment_id": None,
            "protocol_version_id": None,
            "pipeline_version_id": None,
            "reference_dataset_version_id": None,
            "subgroup_field": None,
            "target_column": None,
            "positive_label": None,
            "negative_label": None,
        }
        fp_recomputed = compute_assessment_fingerprint(
            reg.id,
            reg.current_version_id,
            reg.sha256,
            req.thresholds,
            context,
        )
        assert fp_recomputed == sc1_fp


def test_scorecard_comparison_diff():
    # Base dataset: complete, 100 rows
    reg1 = _create_clean_dataset(n_rows=100)

    # Target dataset: 10 rows, high missingness
    df2 = pd.DataFrame({
        "f1": [1.0, np.nan] * 5,
        "f2": [np.nan] * 10,
        "disease_present": ["positive", "negative"] * 5,
    })
    meta2 = DatasetUploadMetadata(name="Degraded Cohort", target="disease_present", positive_label="positive", deidentified=True)
    reg2 = register_csv(df2.to_csv(index=False).encode(), "degraded.csv", meta2)

    with session_scope() as session:
        sc_base = assess_dataset_quality(session, reg1.id, DatasetQualityRequest())
        sc_target = assess_dataset_quality(session, reg2.id, DatasetQualityRequest())

        diff = compare_scorecards(session, sc_base.id, sc_target.id)

        assert diff.base_scorecard_id == sc_base.id
        assert diff.target_scorecard_id == sc_target.id
        assert diff.status_delta["base_status"] == "PASS"
        assert diff.status_delta["target_status"] in ("WARN", "FAIL")
        assert diff.status_delta["changed"] is True
        assert diff.summary_delta["score_delta"] < 0  # Quality score dropped
        assert len(diff.new_failures) > 0


def test_scientific_audit_timeline_events_recorded():
    reg = _create_clean_dataset(n_rows=60)

    with session_scope() as session:
        sc = assess_dataset_quality(session, reg.id, DatasetQualityRequest())

        events = get_events(session, object_id=sc.id)
        assert len(events) >= 1
        comp_event = next(e for e in events if e.event_type == "DATASET_QUALITY_ASSESSMENT_COMPLETED")
        assert comp_event.event_category == "DATASET"
        assert comp_event.source_component == "data_quality_service"
        assert comp_event.metadata["status"] == sc.status


def test_api_endpoints_e2e(client):
    reg = _create_clean_dataset(n_rows=75)

    # 1. Preflight
    pf_resp = client.post(
        f"/api/datasets/{reg.id}/quality-scorecard/preflight",
        json={"thresholds": {"min_row_count": 25}},
    )
    assert pf_resp.status_code == 200
    pf_data = pf_resp.json()
    assert pf_data["dataset_id"] == reg.id
    assert pf_data["ready_to_assess"] is True
    assert "expected_fingerprint" in pf_data

    # 2. Assess
    assess_resp = client.post(
        f"/api/datasets/{reg.id}/quality-scorecard",
        json={"thresholds": {"min_row_count": 25}},
    )
    assert assess_resp.status_code == 200
    sc_data = assess_resp.json()
    assert sc_data["dataset_id"] == reg.id
    assert sc_data["status"] == "PASS"
    sc_id = sc_data["id"]

    # 3. List
    list_resp = client.get(f"/api/datasets/{reg.id}/quality-scorecard")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 4. Get Latest
    latest_resp = client.get(f"/api/datasets/{reg.id}/quality-scorecard/latest")
    assert latest_resp.status_code == 200
    assert latest_resp.json()["id"] == sc_id

    # 5. Get by ID
    get_resp = client.get(f"/api/datasets/{reg.id}/quality-scorecard/{sc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == sc_id

    # 6. Export markdown
    export_resp = client.get(f"/api/datasets/{reg.id}/quality-scorecard/{sc_id}/export?format=markdown")
    assert export_resp.status_code == 200
    assert "# EntangleX Q-Health Dataset Quality Scorecard" in export_resp.text
    assert sc_id in export_resp.text

    # 7. Compare
    comp_resp = client.get(f"/api/datasets/{reg.id}/quality-scorecard/compare?base_id={sc_id}&target_id={sc_id}")
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status_delta"]["changed"] is False
