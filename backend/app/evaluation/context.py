"""Authoritative model evaluation context resolution.

Research analyses must be anchored either to a persisted live Run or to the
immutable verified-demo package.  This module centralizes that decision so
calibration, threshold analysis, diagnostics, and Model Cards cannot silently
invent provenance or mix unrelated records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..api.schemas import TrainingConfig
from ..demo_readiness import ARTIFACT_VERSION, validate_packaged_dataset, verify_installed_model
from ..storage.entities import Dataset, DatasetVersion, Experiment, ModelRecord, Run
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint

LIVE_RUN = "live_run"
VERIFIED_DEMO_EXPERIMENT = "verified_demo_experiment"


@dataclass(frozen=True)
class ModelEvaluationContext:
    model: ModelRecord
    run: Run | None
    experiment: Experiment
    dataset: Dataset
    dataset_version: DatasetVersion | None
    training_config: TrainingConfig
    source_context_type: str
    configuration_fingerprint: str
    provenance: dict[str, Any]

    def source_context(self) -> dict[str, Any]:
        return clean_json({
            "type": self.source_context_type,
            "model_id": self.model.id,
            "experiment_id": self.experiment.id,
            "run_id": self.run.id if self.run else None,
            "dataset_id": self.dataset.id,
            "dataset_version_id": self.dataset_version.id if self.dataset_version else None,
            "dataset_hash": (
                self.dataset_version.content_sha256
                if self.dataset_version else self.dataset.sha256
            ),
            "configuration_fingerprint": self.configuration_fingerprint,
            "model_artifact_sha256": self.model.artifact_sha256,
            "provenance": self.provenance,
        })


def _verified_demo_context(model: ModelRecord, experiment: Experiment, dataset: Dataset) -> dict:
    details = model.details or {}
    if details.get("experiment_kind") != "precomputed_verified_demo":
        raise AppError(
            "source_context_missing",
            "The model has neither a persisted Run nor verified-demo provenance.",
            409,
        )
    slug = (details.get("dataset_provenance") or {}).get("library_slug")
    if not slug:
        raise AppError("demo_provenance_missing", "Verified-demo provenance is incomplete.", 409)
    verify_installed_model(model)
    checked = validate_packaged_dataset(slug)
    packaged_model = next((item for item in checked["models"] if item["id"] == model.id), None)
    if (
        packaged_model is None
        or packaged_model["experiment_id"] != experiment.id
        or packaged_model["dataset_id"] != dataset.id
        or packaged_model["artifact_sha256"] != model.artifact_sha256
        or checked["experiment"]["id"] != experiment.id
        or checked["dataset"]["id"] != dataset.id
        or experiment.config != checked["experiment"]["config"]
        or dataset.sha256 != checked["catalog"]["sha256"]
    ):
        raise AppError(
            "demo_context_mismatch",
            "The verified model, experiment, dataset, and artifact do not form one package.",
            409,
        )
    return {
        "artifact_version": ARTIFACT_VERSION,
        "manifest_sha256": checked["manifest_sha256"],
        "library_slug": slug,
        "dataset_origin": (dataset.provenance or {}).get("origin"),
        "immutable_package": True,
    }


def resolve_model_evaluation_context(
    session,
    model_id: str,
    dataset_id: str,
    dataset_version_id: str | None = None,
) -> ModelEvaluationContext:
    model = session.get(ModelRecord, str(model_id))
    if model is None or model.status != "ready":
        raise AppError("model_unavailable", "The requested model is not available.")
    experiment = session.get(Experiment, model.experiment_id)
    if experiment is None:
        raise AppError("experiment_missing", "The model's source experiment is unavailable.", 409)
    if experiment.dataset_id != model.dataset_id:
        raise AppError("source_context_mismatch", "The model and experiment dataset identities do not match.", 409)

    dataset = session.get(Dataset, str(dataset_id))
    if dataset is None:
        raise AppError("dataset_missing", "Evaluation dataset missing.")
    run = session.get(Run, model.run_id) if model.run_id else None

    if run is not None:
        if run.experiment_id != experiment.id or run.dataset_id != model.dataset_id:
            raise AppError("source_context_mismatch", "The model Run lineage is inconsistent.", 409)
        config_dict = clean_json(run.config or {})
        context_type = LIVE_RUN
        context_provenance = {
            "run_status": run.status,
            "manifest_artifact_id": run.manifest_artifact_id,
            "reproducibility_status": run.reproducibility_status,
        }
        default_version_id = run.dataset_version_id if dataset.id == run.dataset_id else dataset.current_version_id
        config_fingerprint = run.configuration_fingerprint or fingerprint(config_dict)
    else:
        if dataset.id != model.dataset_id:
            raise AppError(
                "demo_dataset_mismatch",
                "Verified-demo analyses must use the packaged verified dataset.",
                409,
            )
        context_provenance = _verified_demo_context(model, experiment, dataset)
        config_dict = clean_json(experiment.config or {})
        context_type = VERIFIED_DEMO_EXPERIMENT
        default_version_id = dataset.current_version_id
        config_fingerprint = fingerprint(config_dict)

    version_id = str(dataset_version_id) if dataset_version_id else default_version_id
    version = session.get(DatasetVersion, version_id) if version_id else None
    if version is not None and version.dataset_id != dataset.id:
        raise AppError("dataset_version_mismatch", "The dataset version does not belong to the evaluation dataset.", 409)
    if dataset_version_id and version is None:
        raise AppError("dataset_version_missing", "Evaluation dataset version missing.", 404)

    try:
        training_config = TrainingConfig.model_validate(config_dict)
    except Exception as exc:
        raise AppError("training_config_invalid", "The authoritative training configuration is invalid.", 409) from exc

    return ModelEvaluationContext(
        model=model,
        run=run,
        experiment=experiment,
        dataset=dataset,
        dataset_version=version,
        training_config=training_config,
        source_context_type=context_type,
        configuration_fingerprint=config_fingerprint,
        provenance=context_provenance,
    )