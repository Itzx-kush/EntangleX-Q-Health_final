"""Deterministic synthetic fixtures for Scientific CI.

Every fixture in this module is synthetic, small, deterministic and
non-sensitive.  Real biomedical datasets, patient-level records, production
snapshots and secrets are never used by Scientific CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

FIXTURE_SEED = 19
"""Single deterministic seed shared by every synthetic fixture."""

ALTERNATE_SEED = 23
"""A second seed used to prove that scientific changes alter fingerprints."""

SUBGROUP_FIELD = "age"
"""Column used by subgroup fixtures."""


# --------------------------------------------------------------------------- #
# Synthetic frames
# --------------------------------------------------------------------------- #
def synthetic_biomedical_frame(n_rows: int = 120, seed: int = FIXTURE_SEED) -> pd.DataFrame:
    """Small synthetic frame with a binary target, a subgroup field and one missing value."""
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(rng.normal(size=(n_rows, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    latent = frame["biomarker_0"] + 0.5 * frame["biomarker_1"] + rng.normal(size=n_rows)
    frame["observed_class"] = np.where(latent > np.median(latent), "positive", "negative")
    frame["age"] = rng.integers(20, 80, size=n_rows)
    frame["sex"] = rng.choice(["female", "male"], size=n_rows)
    frame.loc[3, "biomarker_2"] = np.nan
    return frame


def quality_defect_frame(n_rows: int = 80, seed: int = FIXTURE_SEED) -> pd.DataFrame:
    """Synthetic frame containing known quality defects.

    Contains: missing values, duplicated rows, class imbalance, a constant
    feature and a non-finite numeric value.
    """
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "age": rng.integers(18, 90, size=n_rows).astype(float),
            "cholesterol": rng.normal(200, 25, size=n_rows),
            "constant_marker": np.full(n_rows, 1.0),
            "category": rng.choice(["A", "B"], size=n_rows),
        }
    )
    frame["target"] = np.where(rng.random(n_rows) < 0.9, "positive", "negative")
    frame.loc[0:6, "cholesterol"] = np.nan
    frame.loc[7, "age"] = np.inf
    frame.loc[8, "age"] = -np.inf
    duplicated = frame.iloc[[10, 11, 12]].copy()
    return pd.concat([frame, duplicated], ignore_index=True)


def stratified_metric_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic binary labels, predictions and scores for stratified metrics."""
    rng = np.random.default_rng(FIXTURE_SEED)
    scores = rng.random(60)
    labels = (scores > 0.45).astype(int)
    predictions = (scores > 0.5).astype(int)
    return labels, predictions, scores


# --------------------------------------------------------------------------- #
# Canonical definitions
# --------------------------------------------------------------------------- #
def canonical_pipeline_definition(dataset_id: str | None = None, dataset_version_id: str | None = None) -> dict[str, Any]:
    """Minimal classical pipeline definition with contiguous, ordered stages."""
    return {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "controlled_comparison_protocol_id": None,
        "stages": [
            {
                "stage_order": 1,
                "stage_type": "data_validation",
                "stage_name": "Synthetic validation",
                "configuration": {"minimum_rows": 20},
            },
            {
                "stage_order": 2,
                "stage_type": "preprocessing",
                "stage_name": "Synthetic preprocessing",
                "configuration": {"imputation": "median", "scaling": "standard"},
            },
            {
                "stage_order": 3,
                "stage_type": "feature_engineering",
                "stage_name": "Synthetic feature engineering",
                "configuration": {"operations": ["synthetic_ratio"]},
            },
            {
                "stage_order": 4,
                "stage_type": "representation",
                "stage_name": "Synthetic representation",
                "configuration": {"representation": "dense_numeric"},
            },
            {
                "stage_order": 5,
                "stage_type": "model",
                "stage_name": "Synthetic logistic regression",
                "configuration": {"model_type": "logistic_regression", "seed": FIXTURE_SEED},
            },
            {
                "stage_order": 6,
                "stage_type": "evaluation",
                "stage_name": "Synthetic evaluation",
                "configuration": {"metrics": ["roc_auc", "accuracy"]},
            },
        ],
    }


def canonical_quantum_pipeline_definition() -> dict[str, Any]:
    """Pipeline definition carrying a local-simulator quantum representation stage."""
    definition = canonical_pipeline_definition()
    definition["stages"].insert(
        3,
        {
            "stage_order": 5,
            "stage_type": "quantum_encoding",
            "stage_name": "Synthetic quantum encoding",
            "configuration": {
                "provider_id": "qiskit_local",
                "backend": "statevector",
                "qubits": 4,
                "hardware_execution_claimed": False,
            },
        },
    )
    for index, stage in enumerate(definition["stages"], start=1):
        stage["stage_order"] = index
    return definition


def canonical_protocol_definition(dataset_id: str | None = None) -> dict[str, Any]:
    """Minimal classical experiment protocol definition using the real policy schema."""
    return {
        "schema_version": "protocol_definition_v1",
        "study_metadata": {
            "study_purpose": "Verify protocol machinery with synthetic data only.",
            "task_type": "binary_classification",
            "task_description": "Synthetic Scientific CI protocol fixture.",
            "experiment_scope": "research_benchmark",
        },
        "dataset_policy": {
            "dataset_id": dataset_id,
            "dataset_version_id": None,
            "target_column": "observed_class",
            "positive_label": "positive",
            "negative_label": "negative",
        },
        "split_policy": {
            "strategy": "stratified_kfold",
            "test_size": 0.25,
            "cv_folds": 5,
            "stratify": True,
            "split_seed": FIXTURE_SEED,
        },
        "randomness_policy": {"primary_seed": FIXTURE_SEED, "seed_list": [FIXTURE_SEED], "multi_seed_count": 1},
        "model_policy": {"allowed_model_types": ["logistic_regression"], "model_families": ["classical"]},
        "evaluation_policy": {"primary_metric": "roc_auc", "secondary_metrics": ["accuracy", "f1"]},
        "threshold_policy": {"strategy": "f1_optimal", "lock_threshold": True},
        "calibration_policy": {"method": "isotonic"},
        "constraints": {"minimum_rows": 20},
    }


def canonical_manifest_payload() -> dict[str, Any]:
    """Canonical reproducibility-manifest payload used for fingerprint checks."""
    return {
        "identity": {
            "run_id": "00000000-0000-4000-8000-000000000001",
            "experiment_id": "00000000-0000-4000-8000-000000000002",
            "dataset_id": "00000000-0000-4000-8000-000000000003",
            "manifest_hash": "",
        },
        "dataset": {
            "dataset_id": "00000000-0000-4000-8000-000000000003",
            "sha256": "d" * 64,
            "row_count": 120,
            "feature_count": 6,
            "target": "observed_class",
        },
        "sampling": {"max_samples": None, "sampling_unit": "independent_samples", "duplicate_policy": "drop"},
        "split": {"strategy": "stratified", "test_size": 0.25, "seed": FIXTURE_SEED},
        "cross_validation": {"folds": 5, "strategy": "stratified", "seed": FIXTURE_SEED},
        "preprocessing": {"imputation": "median", "scaling": "standard"},
        "feature_engineering": {"enabled": False, "operations": []},
        "feature_selection": {"enabled": False, "method": None},
        "dimensionality_reduction": {"enabled": False, "components": None},
        "models": [
            {
                "kind": "classical",
                "model_type": "logistic_regression",
                "configuration": {"seed": FIXTURE_SEED, "max_iter": 200},
            }
        ],
        "threshold_protocol": {"strategy": "sensitivity", "target_sensitivity": 0.9},
        "evaluation_protocol": {"metrics": ["roc_auc", "accuracy"], "confidence_level": 0.95},
        "software_environment": {"python": "3.11", "packages": {"numpy": "synthetic"}},
        "runtime_environment": {"platform": "synthetic", "mode": "research"},
        "execution_at_lock": {"locked_at": "2026-01-01T00:00:00+00:00", "job_id": "synthetic"},
        "reproducibility": {"status": "complete", "seeded": True},
    }


def canonical_audit_event_fields() -> dict[str, Any]:
    """Canonical audit-event identity fields for fingerprint determinism checks."""
    return {
        "schema_version": "scientific_audit_event_v1",
        "event_type": "EXPERIMENT_CREATED",
        "event_category": "EXPERIMENT",
        "occurred_at": "2026-01-01T00:00:00+00:00",
        "actor_type": "SYSTEM",
        "actor_reference": None,
        "source_component": "scientific_ci_fixture",
        "object_type": "experiment",
        "object_id": "00000000-0000-4000-8000-000000000004",
        "parent_object_type": None,
        "parent_object_id": None,
        "operation_key": "scientific-ci:fixture:experiment",
        "before_fingerprint": None,
        "after_fingerprint": "e" * 64,
        "previous_event_fingerprint": None,
        "metadata": {"stage": "fixture", "synthetic": True},
    }


def canonical_circuit_configuration() -> dict[str, Any]:
    """Canonical quantum model configuration for circuit fingerprint checks."""
    return {
        "provider_id": "qiskit_local",
        "backend": "statevector",
        "model_type": "vqc",
        "qubits": 4,
        "feature_map": "zz",
        "ansatz": "real_amplitudes",
        "reps": 2,
        "seed": FIXTURE_SEED,
    }


def canonical_subgroup_study_fields() -> dict[str, Any]:
    """Canonical subgroup study identity fields for fingerprint determinism checks."""
    return {
        "experiment_id": "00000000-0000-4000-8000-000000000005",
        "model_id": "00000000-0000-4000-8000-000000000006",
        "dataset_hash": "f" * 64,
        "subgroup_field": SUBGROUP_FIELD,
        "rules": [
            {"id": "younger", "label": "Younger adults", "field": SUBGROUP_FIELD, "operator": "less_than", "value": 50},
            {"id": "older", "label": "Older adults", "field": SUBGROUP_FIELD, "operator": "greater_than_or_equal", "value": 50},
        ],
        "minimum_n": 20,
        "missing_value_policy": "exclude",
        "reference_subgroup_id": None,
        "confidence_level": 0.95,
    }


def canonical_scorecard_assessment_fields() -> dict[str, Any]:
    """Canonical dataset-quality assessment identity fields."""
    return {
        "dataset_id": "00000000-0000-4000-8000-000000000007",
        "dataset_version_id": None,
        "content_sha256": "a" * 64,
        "configuration": {"thresholds": {}, "target_column": "target"},
        "context": {"protocol_version_id": None, "pipeline_version_id": None, "subgroup_field": None},
    }


def canonical_comparison_index() -> dict[str, Any]:
    """Canonical controlled-comparison representation index."""
    return {
        "dataset_version_id": "00000000-0000-4000-8000-000000000008",
        "target_column": "observed_class",
        "positive_label": "positive",
        "test_population_fingerprint": "b" * 64,
        "split_seed": FIXTURE_SEED,
        "preprocessing_fingerprint": "c" * 64,
        "feature_representation": "classical_dense",
    }


# --------------------------------------------------------------------------- #
# Persisted chains
# --------------------------------------------------------------------------- #
@dataclass
class SyntheticChain:
    """Identifiers of one persisted synthetic experiment chain."""

    dataset_id: str
    dataset_version_id: str | None
    experiment_id: str
    run_id: str | None
    model_id: str
    pipeline_version_id: str | None = None
    protocol_version_id: str | None = None
    configuration_fingerprint: str = "0" * 64
    model_type: str = "logistic_regression"
    extra: dict[str, Any] = field(default_factory=dict)


def register_fixture_dataset(
    frame: pd.DataFrame | None = None,
    *,
    name: str = "Synthetic Scientific CI fixture",
    target: str = "observed_class",
    positive_label: str = "positive",
):
    """Register a synthetic frame through the real dataset service."""
    from app.api.schemas import DatasetUploadMetadata
    from app.data.service import register_csv

    payload = (frame if frame is not None else synthetic_biomedical_frame()).to_csv(index=False).encode("utf-8")
    metadata = DatasetUploadMetadata(
        name=name,
        target=target,
        positive_label=positive_label,
        deidentified=True,
    )
    return register_csv(payload, "synthetic-scientific-ci.csv", metadata)


def create_pipeline(session, dataset_id: str, dataset_version_id: str | None = None, *, quantum: bool = False):
    """Create and publish a pipeline version through the real registry service."""
    from app.pipelines.schemas import PipelineCreateRequest
    from app.pipelines.service import create_pipeline_version, publish_pipeline_version

    definition = (
        canonical_quantum_pipeline_definition() if quantum else canonical_pipeline_definition(dataset_id, dataset_version_id)
    )
    version, _created = create_pipeline_version(
        session,
        PipelineCreateRequest(
            pipeline_name="Synthetic Scientific CI pipeline",
            description="Synthetic pipeline fixture; not a research claim.",
            source_context="scientific_ci",
            definition=definition,
        ),
    )
    return publish_pipeline_version(session, version.id)


def create_protocol(session, dataset_id: str | None = None):
    """Create and publish a protocol version through the real registry service."""
    from app.protocols.schemas import ProtocolCreateRequest
    from app.protocols.service import create_protocol_version, publish_protocol_version

    version, _created = create_protocol_version(
        session,
        ProtocolCreateRequest(
            protocol_name="Synthetic Scientific CI protocol",
            description="Synthetic protocol fixture; not a research claim.",
            source_context="scientific_ci",
            definition=canonical_protocol_definition(dataset_id),
        ),
    )
    return publish_protocol_version(session, version.id)


def persist_chain(
    *,
    frame: pd.DataFrame | None = None,
    model_type: str = "logistic_regression",
    with_run: bool = True,
    with_metrics: bool = True,
    with_pipeline: bool = False,
    with_protocol: bool = False,
    legacy: bool = False,
    parent_experiment_id: str | None = None,
    summary: dict[str, Any] | None = None,
) -> SyntheticChain:
    """Persist a small synthetic experiment chain directly, without training.

    ``legacy=True`` omits the optional scientific references that records created
    before the pipeline/protocol registries are allowed to omit.
    """
    from app.database import session_scope
    from app.storage.entities import Experiment, ModelRecord, Run
    from app.utils.serialization import fingerprint

    registered = register_fixture_dataset(frame)
    experiment_id, run_id, model_id = str(uuid4()), str(uuid4()), str(uuid4())
    configuration = {
        "dataset_id": registered.id,
        "dataset_version_id": registered.current_version_id,
        "models": [model_type],
        "seed": FIXTURE_SEED,
        "sampling_unit": "independent_samples",
    }
    pipeline_version_id: str | None = None
    protocol_version_id: str | None = None
    configuration_fingerprint = fingerprint(configuration)

    with session_scope() as session:
        if with_pipeline and not legacy:
            version = create_pipeline(session, registered.id, registered.current_version_id, quantum=model_type != "logistic_regression")
            pipeline_version_id = version.id
        if with_protocol and not legacy:
            protocol = create_protocol(session, registered.id)
            protocol_version_id = protocol.id
        session.add(
            Experiment(
                id=experiment_id,
                name=f"Synthetic Scientific CI experiment {experiment_id[:8]}",
                dataset_id=registered.id,
                parent_id=parent_experiment_id,
                pipeline_version_id=pipeline_version_id,
                protocol_version_id=protocol_version_id,
                protocol_fingerprint=None,
                status="completed",
                config=configuration,
                summary=summary or {"limitations": ["Synthetic fixture only; not a research result."]},
            )
        )
        session.flush()
        if with_run:
            session.add(
                Run(
                    id=run_id,
                    experiment_id=experiment_id,
                    dataset_id=registered.id,
                    dataset_version_id=registered.current_version_id,
                    pipeline_version_id=pipeline_version_id,
                    status="completed",
                    operation_key=f"scientific-ci:{run_id}",
                    config=configuration,
                    execution_metadata={},
                    reproducibility_metadata={"dataset_hash": registered.sha256},
                    result_summary={},
                    configuration_fingerprint=configuration_fingerprint,
                    reproducibility_status="complete",
                )
            )
            session.flush()
        session.add(
            ModelRecord(
                id=model_id,
                experiment_id=experiment_id,
                run_id=run_id if with_run else None,
                dataset_id=registered.id,
                model_type=model_type,
                status="ready",
                artifact_sha256="a" * 64,
                details={"supports_probability": True, "synthetic_fixture": True},
                metrics={"test": {"accuracy": 0.8, "sample_count": 24}} if with_metrics else {},
            )
        )

    return SyntheticChain(
        dataset_id=registered.id,
        dataset_version_id=registered.current_version_id,
        experiment_id=experiment_id,
        run_id=run_id if with_run else None,
        model_id=model_id,
        pipeline_version_id=pipeline_version_id,
        protocol_version_id=protocol_version_id,
        configuration_fingerprint=configuration_fingerprint,
        model_type=model_type,
    )


def canonical_comparison_conditions(
    dataset_id: str,
    dataset_version_id: str | None,
    *,
    target: str = "observed_class",
    dataset_hash: str = "d" * 64,
) -> dict[str, Any]:
    """Canonical persisted comparison conditions used by the controlled-comparison engine."""
    return {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "dataset_hash": dataset_hash,
        "target": target,
        "positive_label": "positive",
        "negative_label": "negative",
        "sample_pool_hash": "1" * 64,
        "test_indices": [1, 2, 3, 4, 5],
        "train_indices": [6, 7, 8, 9, 10],
        "split_hash": "2" * 64,
        "max_samples": None,
        "duplicate_policy": "drop",
        "test_size": 0.25,
        "evaluated_row_count": 30,
        "seed": FIXTURE_SEED,
        "cv_folds": 5,
        "threshold_strategy": "sensitivity",
        "target_sensitivity": 0.9,
        "representation": {
            "raw_input_features": ["biomarker_0", "biomarker_1"],
            "pipeline": {"stages": ["preprocessing", "representation"]},
            "pca_components": 4,
            "angle_scaling": "pi_over_2",
        },
    }


@dataclass
class ComparisonPair:
    """Identifiers of a persisted classical/quantum pair inside one experiment."""

    experiment_id: str
    dataset_id: str
    dataset_version_id: str | None
    classical_model_id: str
    quantum_model_id: str


def persist_comparison_pair(*, quantum_target: str | None = None) -> ComparisonPair:
    """Persist one experiment holding a classical and a quantum-family model.

    The models carry explicit persisted comparison conditions, so the
    controlled-comparison engine evaluates real parity evidence without training.
    """
    from app.database import session_scope
    from app.storage.entities import Experiment, ModelRecord, Run
    from app.utils.serialization import fingerprint

    registered = register_fixture_dataset()
    experiment_id, run_id = str(uuid4()), str(uuid4())
    classical_model_id, quantum_model_id = str(uuid4()), str(uuid4())
    config = {
        "dataset_id": registered.id,
        "dataset_version_id": registered.current_version_id,
        "models": ["logistic_regression", "vqc"],
        "seed": FIXTURE_SEED,
        "sampling_unit": "independent_samples",
    }
    split = {"strategy": "stratified", "test_size": 0.25, "seed": FIXTURE_SEED}

    with session_scope() as session:
        session.add(
            Experiment(
                id=experiment_id,
                name=f"Synthetic controlled comparison {experiment_id[:8]}",
                dataset_id=registered.id,
                status="completed",
                config=config,
                summary={"split": split, "limitations": ["Synthetic fixture only."]},
            )
        )
        session.flush()
        session.add(
            Run(
                id=run_id,
                experiment_id=experiment_id,
                dataset_id=registered.id,
                dataset_version_id=registered.current_version_id,
                status="completed",
                operation_key=f"scientific-ci:comparison:{run_id}",
                config=config,
                execution_metadata={},
                reproducibility_metadata={"dataset_hash": registered.sha256},
                result_summary={},
                configuration_fingerprint=fingerprint(config),
                reproducibility_status="complete",
            )
        )
        session.flush()
        session.add(
            ModelRecord(
                id=classical_model_id,
                experiment_id=experiment_id,
                run_id=run_id,
                dataset_id=registered.id,
                model_type="logistic_regression",
                status="ready",
                artifact_sha256="a" * 64,
                details={
                    "comparison_conditions": canonical_comparison_conditions(
                        registered.id, registered.current_version_id, dataset_hash=registered.sha256
                    ),
                    "configuration": config,
                    "split": split,
                    "supports_probability": True,
                },
                metrics={"test": {"accuracy": 0.81, "roc_auc": 0.84, "sample_count": 30}},
            )
        )
        session.add(
            ModelRecord(
                id=quantum_model_id,
                experiment_id=experiment_id,
                run_id=run_id,
                dataset_id=registered.id,
                model_type="vqc",
                status="ready",
                artifact_sha256="b" * 64,
                details={
                    "comparison_conditions": canonical_comparison_conditions(
                        registered.id,
                        registered.current_version_id,
                        target=quantum_target or "observed_class",
                        dataset_hash=registered.sha256,
                    ),
                    "configuration": config,
                    "split": split,
                    "quantum": {
                        "provider_id": "qiskit_local",
                        "backend_id": "statevector",
                        "execution_mode": "local_simulator",
                        "qubits": 4,
                        "real_hardware": False,
                    },
                },
                metrics={"test": {"accuracy": 0.79, "roc_auc": 0.82, "sample_count": 30}},
            )
        )

    return ComparisonPair(
        experiment_id=experiment_id,
        dataset_id=registered.id,
        dataset_version_id=registered.current_version_id,
        classical_model_id=classical_model_id,
        quantum_model_id=quantum_model_id,
    )
