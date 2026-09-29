"""Authoritative verified instant-demo configuration and package lifecycle."""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from threading import RLock

from .api.schemas import TrainingConfig
from .data.catalog import builtin_bytes, list_builtin_datasets
from .database import session_scope
from .storage.entities import Dataset, Experiment, Job, ModelRecord
from .storage.files import RestrictedUnpickler, atomic_bytes, safe_path
from .utils.errors import AppError

ARTIFACT_SCHEMA_VERSION = 2
ARTIFACT_VERSION = "sih-verified-demo-v2"
PACKAGED_ARTIFACT_HASH_ALGORITHM = "sha256"
PACKAGED_ARTIFACT_HASH_SCOPE = "raw_dill_payload"
# Deliberately explicit and centralized. Availability does not imply scientific superiority.
READY_DEMO_DATASETS = frozenset({"wdbc", "early-stage-diabetes"})
EXPECTED_BUILTIN_COUNT = 5
EXPECTED_READY_COUNT = 2

_lock = RLock()
_manifest_cache: dict | None = None
# Only successfully validated entries may have available=True. Failed states are cached closed.
_verification_cache: dict[str, dict] | None = None


def validate_readiness_configuration(ready_slugs: set[str] | frozenset[str] = READY_DEMO_DATASETS) -> None:
    slugs = {entry["slug"] for entry in list_builtin_datasets(include_readiness=False)}
    if len(slugs) != EXPECTED_BUILTIN_COUNT:
        raise AppError("demo_readiness_config_invalid", "Exactly five built-in datasets are required.", 500)
    unknown = set(ready_slugs) - slugs
    if len(ready_slugs) != EXPECTED_READY_COUNT or unknown or len(slugs - set(ready_slugs)) != 3:
        raise AppError("demo_readiness_config_invalid", "Verified demo readiness must select exactly two of the five built-in dataset slugs.", 500)


def _root():
    return files("app.demo_artifacts")


def _canonical_manifest(value: dict) -> bytes:
    unsigned = {key: item for key, item in value.items() if key != "manifest_sha256"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_manifest(*, refresh: bool = False) -> dict:
    global _manifest_cache
    validate_readiness_configuration()
    if _manifest_cache is not None and not refresh:
        return _manifest_cache
    try:
        value = json.loads(_root().joinpath("manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise AppError("demo_manifest_unavailable", "The verified demo artifact manifest is unavailable.", 503) from exc
    if value.get("schema_version") != ARTIFACT_SCHEMA_VERSION or value.get("artifact_version") != ARTIFACT_VERSION:
        raise AppError("demo_manifest_unsupported", "The verified demo artifact manifest version is unsupported.", 409)
    expected = value.get("manifest_sha256", "")
    actual = hashlib.sha256(_canonical_manifest(value)).hexdigest()
    if not expected or not hmac.compare_digest(expected, actual):
        raise AppError("demo_manifest_integrity", "The verified demo artifact manifest failed its integrity check.", 409)
    entries = value.get("datasets")
    if not isinstance(entries, dict) or set(entries) != set(READY_DEMO_DATASETS):
        raise AppError("demo_manifest_invalid", "The verified demo artifact manifest does not match the readiness configuration.", 409)
    _manifest_cache = value
    return value


def _artifact_path(filename: str) -> Path:
    if not filename or Path(filename).name != filename or not filename.endswith(".dill.b64"):
        raise AppError("demo_manifest_invalid", "A packaged model artifact reference is invalid.", 409)
    return Path(str(_root().joinpath("models", filename)))


def _artifact_payload(path: Path) -> bytes:
    if not path.is_file():
        raise AppError("demo_artifact_missing", "A verified demo model artifact is missing.", 409)
    try:
        return base64.b64decode(path.read_bytes(), validate=True)
    except (ValueError, TypeError) as exc:
        raise AppError("demo_artifact_invalid", "A verified demo model artifact encoding is invalid.", 409) from exc


def packaged_artifact_sha256(payload: bytes) -> str:
    """SHA-256 of decoded raw dill bytes; separate from live storage's HMAC integrity value."""
    return hashlib.sha256(payload).hexdigest()


def _read_bundle(path: Path, expected_sha256: str) -> dict:
    payload = _artifact_payload(path)
    if packaged_artifact_sha256(payload) != expected_sha256:
        raise AppError("demo_artifact_integrity", "A verified demo model artifact failed its SHA-256 integrity check.", 409)
    try:
        return RestrictedUnpickler(io.BytesIO(payload)).load()
    except Exception as exc:
        raise AppError("demo_artifact_invalid", "A verified demo model artifact could not be loaded safely.", 409) from exc


def _validate_timestamp(value: object, field: str) -> None:
    try:
        datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise AppError("demo_manifest_invalid", f"The verified demo {field} timestamp is invalid.", 409) from exc


def _validate_entry(slug: str, entry: dict, manifest: dict) -> dict:
    catalog, dataset_bytes = builtin_bytes(slug)
    if entry.get("slug") != slug or entry.get("dataset_sha256") != catalog["sha256"]:
        raise AppError("demo_dataset_mismatch", "The verified demo artifact does not match the packaged dataset.", 409)
    dataset = entry.get("dataset") or {}
    experiment = entry.get("experiment") or {}
    job = entry.get("job") or {}
    models = entry.get("models") or []
    dataset_id, experiment_id = dataset.get("id"), experiment.get("id")
    provenance = dataset.get("provenance", {})
    if (not dataset_id or dataset.get("sha256") != catalog["sha256"] or provenance.get("library_slug") != slug
            or provenance.get("target") != catalog["target"] or provenance.get("positive_label") != catalog["positive_label"]
            or provenance.get("negative_label") != catalog["negative_label"] or provenance.get("origin") != "built_in"):
        raise AppError("demo_dataset_mismatch", "The verified demo dataset identity, target, or labels are invalid.", 409)
    if experiment.get("dataset_id") != dataset_id or experiment.get("status") != "succeeded":
        raise AppError("demo_experiment_mismatch", "The verified demo experiment identity is invalid.", 409)
    config = TrainingConfig.model_validate(experiment.get("config"))
    if str(config.dataset_id) != dataset_id:
        raise AppError("demo_experiment_mismatch", "The verified demo experiment configuration is incompatible.", 409)
    summary_provenance = experiment.get("summary", {}).get("dataset_provenance", {})
    if (experiment.get("summary", {}).get("experiment_kind") != "precomputed_verified_demo"
            or summary_provenance.get("library_slug") != slug or summary_provenance.get("dataset_hash") != catalog["sha256"]):
        raise AppError("demo_experiment_mismatch", "The verified demo experiment provenance is incompatible.", 409)
    if (not job.get("id") or job.get("experiment_id") != experiment_id or job.get("status") != "succeeded"
            or job.get("progress") != 100 or not isinstance(job.get("state"), str)
            or not job.get("state") or not isinstance(job.get("errors"), list)):
        raise AppError("demo_job_mismatch", "The verified demo completed-job record is invalid.", 409)
    _validate_timestamp(job.get("created_at"), "job created_at")
    _validate_timestamp(job.get("updated_at"), "job updated_at")
    if not models:
        raise AppError("demo_manifest_invalid", "A verified demo experiment must contain at least one real model.", 409)
    seen = set()
    for model in models:
        if model.get("id") in seen or model.get("experiment_id") != experiment_id or model.get("dataset_id") != dataset_id or model.get("status") != "ready":
            raise AppError("demo_model_mismatch", "A verified demo model relationship is invalid.", 409)
        seen.add(model.get("id"))
        artifact = model.get("artifact") or {}
        if (artifact.get("hash_algorithm") != PACKAGED_ARTIFACT_HASH_ALGORITHM
                or artifact.get("hash_scope") != PACKAGED_ARTIFACT_HASH_SCOPE
                or model.get("artifact_sha256") != artifact.get("sha256")):
            raise AppError("demo_model_mismatch", "A verified demo model SHA-256 contract is inconsistent.", 409)
        bundle = _read_bundle(_artifact_path(artifact.get("filename", "")), artifact.get("sha256", ""))
        model_provenance = model.get("details", {}).get("dataset_provenance", {})
        if (bundle.get("dataset_id") != dataset_id or bundle.get("dataset_hash") != catalog["sha256"]
                or bundle.get("config") != experiment.get("config") or model_provenance.get("library_slug") != slug
                or model_provenance.get("dataset_hash") != catalog["sha256"]
                or model.get("details", {}).get("configuration") != experiment.get("config")):
            raise AppError("demo_model_mismatch", "A verified demo model is incompatible with its dataset or experiment.", 409)
    return {"catalog": catalog, "dataset_bytes": dataset_bytes, "dataset": dataset, "experiment": experiment,
            "job": job, "models": models, "manifest_sha256": manifest["manifest_sha256"]}


def clear_verified_readiness_cache(*, clear_manifest: bool = False) -> None:
    """Explicit test/maintenance refresh hook; never marks an unverified entry ready."""
    global _verification_cache, _manifest_cache
    with _lock:
        _verification_cache = None
        if clear_manifest:
            _manifest_cache = None


def verify_packaged_readiness(*, refresh: bool = False) -> dict[str, dict]:
    """Run the expensive package verification once, then cache only verified metadata."""
    global _verification_cache, _manifest_cache
    validate_readiness_configuration()
    with _lock:
        if _verification_cache is not None and not refresh:
            return _verification_cache
        if refresh:
            _manifest_cache = None
        states: dict[str, dict] = {}
        try:
            manifest = _load_manifest(refresh=refresh)
        except AppError as exc:
            states = {slug: {"available": False, "code": exc.code} for slug in READY_DEMO_DATASETS}
        else:
            for slug in sorted(READY_DEMO_DATASETS):
                try:
                    states[slug] = {"available": True, "code": "verified", "checked": _validate_entry(slug, manifest["datasets"][slug], manifest)}
                except AppError as exc:
                    states[slug] = {"available": False, "code": exc.code}
        _verification_cache = states
        return states


def validate_packaged_dataset(slug: str, *, refresh: bool = False) -> dict:
    if slug not in READY_DEMO_DATASETS:
        raise AppError("demo_not_configured", "No precomputed demo result is packaged for this dataset.", 404)
    state = verify_packaged_readiness(refresh=refresh).get(slug, {"available": False, "code": "demo_unavailable"})
    if not state.get("available") or "checked" not in state:
        raise AppError(state.get("code", "demo_unavailable"), "The verified demo package is unavailable.", 409)
    return state["checked"]


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def install_verified_demo_artifacts() -> None:
    """Startup verification plus idempotent hydration into the existing runtime registry."""
    states = verify_packaged_readiness()
    with _lock:
        for slug in sorted(READY_DEMO_DATASETS):
            state = states.get(slug, {})
            if not state.get("available"):
                continue
            checked = state["checked"]
            dataset_data, experiment_data, job_data, models_data = checked["dataset"], checked["experiment"], checked["job"], checked["models"]
            try:
                dataset_path = safe_path("data/datasets", dataset_data["id"], ".csv")
                if not dataset_path.is_file() or hashlib.sha256(dataset_path.read_bytes()).hexdigest() != checked["catalog"]["sha256"]:
                    atomic_bytes(dataset_path, checked["dataset_bytes"])
                for model in models_data:
                    source = _artifact_path(model["artifact"]["filename"])
                    target = safe_path("models", model["id"], ".dill")
                    if not target.is_file() or packaged_artifact_sha256(target.read_bytes()) != model["artifact_sha256"]:
                        atomic_bytes(target, _artifact_payload(source))
                with session_scope() as session:
                    existing_dataset = session.get(Dataset, dataset_data["id"])
                    if existing_dataset is None:
                        session.add(Dataset(**{**dataset_data, "created_at": _datetime(dataset_data["created_at"])}))
                    elif existing_dataset.sha256 != dataset_data["sha256"] or existing_dataset.provenance.get("library_slug") != slug:
                        raise AppError("demo_dataset_mismatch", "A runtime dataset conflicts with the verified demo identity.", 409)
                    existing_experiment = session.get(Experiment, experiment_data["id"])
                    if existing_experiment is None:
                        session.add(Experiment(**{**experiment_data, "created_at": _datetime(experiment_data["created_at"])}))
                    elif existing_experiment.dataset_id != dataset_data["id"] or existing_experiment.config != experiment_data["config"]:
                        raise AppError("demo_experiment_mismatch", "A runtime experiment conflicts with the verified demo identity.", 409)
                    existing_job = session.get(Job, job_data["id"])
                    if existing_job is None:
                        session.add(Job(**{**job_data, "created_at": _datetime(job_data["created_at"]), "updated_at": _datetime(job_data["updated_at"])}))
                    elif (existing_job.experiment_id != experiment_data["id"] or existing_job.status != "succeeded"
                            or existing_job.progress != 100 or existing_job.errors != job_data["errors"]):
                        raise AppError("demo_job_mismatch", "A runtime job conflicts with the verified demo experiment.", 409)
                    for model_data in models_data:
                        stored = {key: value for key, value in model_data.items() if key != "artifact"}
                        existing_model = session.get(ModelRecord, stored["id"])
                        if existing_model is None:
                            session.add(ModelRecord(**{**stored, "created_at": _datetime(stored["created_at"])}))
                        elif (existing_model.experiment_id != experiment_data["id"] or existing_model.dataset_id != dataset_data["id"]
                                or existing_model.artifact_sha256 != stored["artifact_sha256"]):
                            raise AppError("demo_model_mismatch", "A runtime model conflicts with the verified demo identity.", 409)
            except AppError as exc:
                state.clear()
                state.update({"available": False, "code": exc.code})


def _processing_readiness(*, unavailable_reason: str | None = None) -> dict:
    value = {"status": "requires_processing", "instant_demo_available": False, "artifact_version": None,
             "experiment_id": None, "model_ids": [], "verified_dataset_hash": None,
             "verified_artifact_manifest_hash": None}
    if unavailable_reason:
        value["artifact_version"] = ARTIFACT_VERSION
        value["unavailable_reason"] = unavailable_reason
    return value


def readiness_for(slug: str) -> dict:
    validate_readiness_configuration()
    if slug not in READY_DEMO_DATASETS:
        return _processing_readiness()
    state = verify_packaged_readiness().get(slug, {})
    if not state.get("available") or "checked" not in state:
        return _processing_readiness(unavailable_reason=state.get("code", "demo_unavailable"))
    checked = state["checked"]
    return {"status": "ready", "instant_demo_available": True, "artifact_version": ARTIFACT_VERSION,
            "experiment_id": checked["experiment"]["id"], "model_ids": [model["id"] for model in checked["models"]],
            "verified_dataset_hash": checked["catalog"]["sha256"],
            "verified_artifact_manifest_hash": checked["manifest_sha256"]}


def readiness_for_registered_dataset(dataset: Dataset) -> dict:
    provenance = dataset.provenance or {}
    if provenance.get("origin") != "built_in" or not provenance.get("library_slug"):
        return _processing_readiness()
    return readiness_for(provenance["library_slug"])


def readiness_summary() -> dict:
    datasets = [{"slug": item["slug"], "dataset_status": item["dataset_status"], "demo_readiness": readiness_for(item["slug"])}
                for item in list_builtin_datasets(include_readiness=False)]
    ready = sum(item["demo_readiness"]["status"] == "ready" for item in datasets)
    return {"total": len(datasets), "verified_demo_ready": ready, "requires_processing": len(datasets) - ready, "datasets": datasets}


def verify_installed_model(record: ModelRecord) -> None:
    slug = record.details.get("dataset_provenance", {}).get("library_slug")
    if record.details.get("experiment_kind") != "precomputed_verified_demo":
        return
    checked = validate_packaged_dataset(slug)
    model = next((item for item in checked["models"] if item["id"] == record.id), None)
    if model is None or model["experiment_id"] != record.experiment_id or model["dataset_id"] != record.dataset_id or model["artifact_sha256"] != record.artifact_sha256:
        raise AppError("demo_model_mismatch", "The verified demo model relationship is invalid.", 409)
    runtime_path = safe_path("models", record.id, ".dill")
    if not runtime_path.is_file() or packaged_artifact_sha256(runtime_path.read_bytes()) != record.artifact_sha256:
        raise AppError("demo_artifact_integrity", "The installed verified demo model failed its packaged SHA-256 integrity check.", 409)
    with session_scope() as session:
        experiment = session.get(Experiment, record.experiment_id)
        dataset = session.get(Dataset, record.dataset_id)
        if experiment is None or dataset is None or experiment.dataset_id != record.dataset_id or dataset.sha256 != checked["catalog"]["sha256"]:
            raise AppError("demo_model_mismatch", "The installed verified demo registry relationships are invalid.", 409)
