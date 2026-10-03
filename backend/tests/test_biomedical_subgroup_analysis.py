from uuid import uuid4
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import inspect, select

from app.api.schemas import DatasetUploadMetadata, TrainingConfig
from app.data.service import register_csv
from app.database import engine, session_scope
from app.evidence_packages.service import preflight_package
from app.experiments.reports import html_report, report_data
from app.lineage.service import lineage_snapshot
from app.storage.entities import Experiment, ModelRecord, Run, SubgroupAnalysisStudy
from app.subgroups.schemas import SubgroupAnalysisRequest, SubgroupRule
from app.subgroups.service import (
    compute_auc_ci,
    compute_study_fingerprint,
    compute_wilson_ci,
    create_subgroup_study,
    derive_predefined_rules,
    evaluate_subgroup_mask,
    export_study,
    get_study,
    list_studies_for_experiment,
    run_preflight,
)


@pytest.fixture
def cohort_dataset():
    """Create a dataset with clear biomedical cohorts (Age bands, Gender, Comorbidities)."""
    rng = np.random.default_rng(42)
    n = 200
    ages = rng.integers(25, 80, size=n)
    genders = rng.choice(["Male", "Female"], size=n)
    comorbidities = rng.choice(["None", "Hypertension", "Diabetes"], size=n)
    bio0 = rng.normal(size=n)
    bio1 = rng.normal(size=n)

    # Outcome correlated with age and bio0
    logits = 0.05 * (ages - 50) + 1.2 * bio0 + rng.normal(scale=0.5, size=n)
    outcome = np.where(logits > np.median(logits), "1", "0")

    frame = pd.DataFrame({
        "age": ages,
        "gender": genders,
        "comorbidity": comorbidities,
        "biomarker_0": bio0,
        "biomarker_1": bio1,
        "Outcome": outcome,
    })
    # Add a couple missing values to gender to test missing value policy
    frame.loc[5, "gender"] = None
    frame.loc[12, "gender"] = None

    metadata = DatasetUploadMetadata(
        name="Biomedical Subgroup Fixture",
        target="Outcome",
        positive_label="1",
        deidentified=True,
    )
    return register_csv(frame.to_csv(index=False).encode(), "cohorts.csv", metadata)


@pytest.fixture
def trained_experiment(cohort_dataset):
    """Set up an experiment with an associated ModelRecord and Run."""
    experiment_id = str(uuid4())
    run_id = str(uuid4())
    model_id = str(uuid4())

    cfg = TrainingConfig(
        dataset_id=cohort_dataset.id,
        models=["logistic_regression"],
        test_size=0.2,
        seed=42,
        max_samples=None,
    )
    training_config = cfg.model_dump(mode="json")

    with session_scope() as session:
        experiment = Experiment(
            id=experiment_id,
            name="Subgroup Analysis Test Experiment",
            dataset_id=cohort_dataset.id,
            status="completed",
            config=training_config,
            summary={
                "dataset_provenance": cohort_dataset.provenance,
                "split": {"test_size": 0.25, "seed": 42},
                "limitations": [],
            },
        )
        session.add(experiment)
        session.flush()

        run = Run(
            id=run_id,
            experiment_id=experiment_id,
            dataset_id=cohort_dataset.id,
            dataset_version_id=cohort_dataset.current_version_id,
            status="completed",
            operation_key=f"subgroup-test-run:{run_id}",
            config=training_config,
            execution_metadata={},
            reproducibility_metadata={"split_seed": 42},
            result_summary={},
            configuration_fingerprint="f" * 64,
            reproducibility_status="complete",
        )
        session.add(run)
        session.flush()

        model = ModelRecord(
            id=model_id,
            experiment_id=experiment_id,
            run_id=run_id,
            dataset_id=cohort_dataset.id,
            model_type="logistic_regression",
            status="ready",
            artifact_sha256="m" * 64,
            details={"supports_probability": True},
            metrics={
                "test": {"accuracy": 0.82, "roc_auc": 0.88, "sample_count": 50},
                "operating_point": {"threshold": 0.5, "locked": True},
            },
        )
        session.add(model)
        session.flush()

    return experiment_id, model_id, run_id


def test_subgroup_database_and_migration():
    """Verify subgroup_analysis_studies table and index structures exist."""
    inspector = inspect(engine)
    assert "subgroup_analysis_studies" in inspector.get_table_names()

    columns = {col["name"] for col in inspector.get_columns("subgroup_analysis_studies")}
    assert {
        "id", "schema_version", "experiment_id", "model_id", "run_id",
        "dataset_id", "status", "operation_key", "definition_fingerprint",
        "subgroup_field", "configuration", "overall_population", "subgroups_results",
        "comparisons", "limitations", "provenance", "created_at",
    }.issubset(columns)

    indices = {idx["name"] for idx in inspector.get_indexes("subgroup_analysis_studies")}
    assert "ix_subgroup_studies_experiment_id" in indices
    assert "ix_subgroup_studies_field" in indices


def test_wilson_and_auc_ci_calculations():
    """Verify statistical confidence interval routines."""
    # Wilson score CI
    lo, hi = compute_wilson_ci(k=80, n=100, confidence_level=0.95)
    assert 0.70 < lo < 0.80
    assert 0.80 < hi < 0.90
    assert lo < hi

    # Boundary conditions
    lo_0, hi_0 = compute_wilson_ci(k=0, n=20, confidence_level=0.95)
    assert lo_0 == 0.0
    assert hi_0 > 0.0

    # Hanley-McNeil AUC CI
    auc_lo, auc_hi = compute_auc_ci(auc=0.85, n_pos=50, n_neg=50, confidence_level=0.95)
    assert 0.75 < auc_lo < 0.85
    assert 0.85 < auc_hi < 0.95


def test_subgroup_preflight_validation(trained_experiment):
    """Test preflight checking logic for valid, invalid, and target fields."""
    experiment_id, model_id, _ = trained_experiment

    # Valid field: age
    req_valid = SubgroupAnalysisRequest(subgroup_field="age", minimum_n=10)
    preflight = run_preflight(experiment_id, req_valid)
    assert preflight.feasible is True
    assert preflight.subgroup_field == "age"
    assert len(preflight.suggested_rules) >= 2
    assert len(preflight.blockers) == 0

    # Non-existent field
    req_invalid = SubgroupAnalysisRequest(subgroup_field="non_existent_column")
    preflight_invalid = run_preflight(experiment_id, req_invalid)
    assert preflight_invalid.feasible is False
    assert any("not found" in b for b in preflight_invalid.blockers)

    # Target field cannot be used as subgroup field
    req_target = SubgroupAnalysisRequest(subgroup_field="Outcome")
    preflight_target = run_preflight(experiment_id, req_target)
    assert preflight_target.feasible is False
    assert any("target column" in b for b in preflight_target.blockers)

    # Missing value policy = error on column with missing values
    req_missing_err = SubgroupAnalysisRequest(subgroup_field="gender", missing_value_policy="error")
    preflight_missing = run_preflight(experiment_id, req_missing_err)
    assert preflight_missing.feasible is False
    assert any("missing values" in b for b in preflight_missing.blockers)


def test_subgroup_analysis_execution_and_metrics(trained_experiment):
    """Execute stratified evaluation on age bands and verify metrics & CIs."""
    experiment_id, model_id, _ = trained_experiment

    req = SubgroupAnalysisRequest(
        subgroup_field="age",
        minimum_n=10,
        missing_value_policy="exclude",
    )
    study = create_subgroup_study(experiment_id, req)

    assert study.id is not None
    assert study.status == "completed"
    assert study.subgroup_field == "age"
    assert len(study.definition_fingerprint) == 64
    assert study.overall_population["n"] == 40
    assert len(study.subgroups_results) >= 2

    # Check first subgroup metrics
    first_group = study.subgroups_results[0]
    assert first_group.population.n > 0
    assert first_group.status in ["VALID", "TOO_SMALL"]

    if first_group.status == "VALID":
        acc = first_group.metrics["accuracy"]
        assert acc.status == "AVAILABLE"
        assert acc.ci_method == "wilson_score"
        assert acc.ci_lower is not None
        assert acc.ci_upper is not None
        assert acc.ci_lower <= acc.value <= acc.ci_upper

    # Check comparisons
    assert len(study.comparisons) == len(study.subgroups_results)


def test_small_subgroup_protection_withheld(trained_experiment):
    """Verify that cohorts below minimum_n have metrics WITHHELD."""
    experiment_id, model_id, _ = trained_experiment

    # Create a rule matching a tiny age slice (e.g., age >= 75)
    tiny_rule = SubgroupRule(
        id="age_tiny",
        label="Elderly 75+",
        field="age",
        operator="greater_than",
        value=74,
    )

    req = SubgroupAnalysisRequest(
        subgroup_field="age",
        subgroup_rules=[tiny_rule],
        minimum_n=30,  # High minimum_n threshold
    )
    study = create_subgroup_study(experiment_id, req)

    assert len(study.subgroups_results) == 1
    result = study.subgroups_results[0]
    assert result.status == "TOO_SMALL"
    assert "minimum_n" in result.status_reason

    # All metrics must be WITHHELD
    for metric_name in ["accuracy", "recall", "specificity", "roc_auc"]:
        val = result.metrics[metric_name]
        assert val.status == "WITHHELD"
        assert val.value is None
        assert "minimum_n" in val.reason


def test_single_class_target_distribution_undefined(trained_experiment):
    """Verify that single-class target within a cohort sets ROC-AUC and PR-AUC to UNDEFINED."""
    experiment_id, model_id, _ = trained_experiment

    # Custom rule with minimum_n=1 to allow evaluation even for small cohorts
    # In a synthetic cohort if all are positive/negative, auc must be UNDEFINED
    single_class_rule = SubgroupRule(
        id="age_very_young",
        label="Young (<30)",
        field="age",
        operator="less_than",
        value=30,
    )

    req = SubgroupAnalysisRequest(
        subgroup_field="age",
        subgroup_rules=[single_class_rule],
        minimum_n=1,
    )
    study = create_subgroup_study(experiment_id, req)
    result = study.subgroups_results[0]

    # If the subgroup happened to have only positive or negative, AUC must be UNDEFINED with reason
    if result.population.positive_n == 0 or result.population.negative_n == 0:
        assert result.metrics["roc_auc"].status == "UNDEFINED"
        assert "single observed target class" in result.metrics["roc_auc"].reason
        assert result.metrics["pr_auc"].status == "UNDEFINED"


def test_missing_value_policy_handling(trained_experiment):
    """Test exclude vs separate_unknown_group missing value policies."""
    experiment_id, model_id, _ = trained_experiment

    # Gender column has 2 missing values
    req_unknown = SubgroupAnalysisRequest(
        subgroup_field="gender",
        missing_value_policy="separate_unknown_group",
        minimum_n=1,
    )
    study_unknown = create_subgroup_study(experiment_id, req_unknown)

    # Must contain a subgroup for Unknown / Missing
    labels = [s.label for s in study_unknown.subgroups_results]
    assert any("Unknown" in lbl or "Missing" in lbl for lbl in labels)


def test_idempotency_and_deterministic_fingerprint(trained_experiment):
    """Verify deterministic fingerprinting and idempotency via operation_key."""
    experiment_id, model_id, _ = trained_experiment

    req = SubgroupAnalysisRequest(
        subgroup_field="age",
        minimum_n=15,
        missing_value_policy="exclude",
    )

    study_1 = create_subgroup_study(experiment_id, req)
    study_2 = create_subgroup_study(experiment_id, req)

    assert study_1.id == study_2.id
    assert study_1.definition_fingerprint == study_2.definition_fingerprint


def test_zero_patient_leakage_in_study_outputs(trained_experiment):
    """Verify that zero patient identifiers or raw records leak into outputs."""
    experiment_id, _, _ = trained_experiment

    req = SubgroupAnalysisRequest(subgroup_field="age", minimum_n=5)
    study = create_subgroup_study(experiment_id, req)
    exported = export_study(study.id)

    serialized = str(exported)
    assert "patient_id" not in serialized
    assert "row_id" not in serialized
    assert "subject_id" not in serialized
    assert "raw_patient_rows" not in serialized


def test_api_endpoints_workflow(client, trained_experiment):
    """Verify REST API endpoints for preflight, execution, query, and export."""
    experiment_id, _, _ = trained_experiment

    # 1. Preflight
    res_pf = client.post(
        f"/api/experiments/{experiment_id}/subgroup-analysis/preflight",
        json={"subgroup_field": "age", "minimum_n": 10},
    )
    assert res_pf.status_code == 200
    pf_data = res_pf.json()
    assert pf_data["feasible"] is True
    assert pf_data["subgroup_field"] == "age"

    # 2. Run Subgroup Analysis
    res_run = client.post(
        f"/api/experiments/{experiment_id}/subgroup-analysis",
        json={"subgroup_field": "age", "minimum_n": 10},
    )
    assert res_run.status_code == 200
    study_data = res_run.json()
    study_id = study_data["id"]
    assert study_data["status"] == "completed"

    # 3. List Studies
    res_list = client.get(f"/api/experiments/{experiment_id}/subgroup-analysis")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 4. Get Study
    res_get = client.get(f"/api/experiments/{experiment_id}/subgroup-analysis/{study_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == study_id

    # 5. Export Study
    res_export = client.get(f"/api/experiments/{experiment_id}/subgroup-analysis/{study_id}/export")
    assert res_export.status_code == 200
    assert res_export.headers["content-type"].startswith("application/json")
    export_body = res_export.json()
    assert export_body["schema_version"] == "subgroup_analysis_v1"
    assert export_body["study"]["id"] == study_id

    # 6. Not Found
    res_nf = client.get(f"/api/experiments/{experiment_id}/subgroup-analysis/{uuid4()}")
    assert res_nf.status_code == 404


def test_subgroup_lineage_and_evidence_integration(trained_experiment):
    """Verify SubgroupAnalysisStudy integration with Lineage and Evidence Packages."""
    experiment_id, _, _ = trained_experiment

    req = SubgroupAnalysisRequest(subgroup_field="age", minimum_n=5)
    study = create_subgroup_study(experiment_id, req)

    # Evidence Packages preflight
    with session_scope() as session:
        pkg_pf = preflight_package(session, experiment_id)
        assert "subgroup_analysis" in pkg_pf["evidence_inventory"]
        assert pkg_pf["evidence_inventory"]["subgroup_analysis"]["status"] == "available"
        assert study.id in pkg_pf["evidence_inventory"]["subgroup_analysis"]["referenced_ids"]

    # Lineage snapshot
    with session_scope() as session:
        snapshot = lineage_snapshot(session, experiment_id)
        assert snapshot is not None

    # Reports
    data = report_data(experiment_id)
    assert "subgroup_analysis" in data
    assert len(data["subgroup_analysis"]) >= 1

    html = html_report(experiment_id)
    assert "Biomedical Subgroup Analysis and Stratified Evaluation" in html
