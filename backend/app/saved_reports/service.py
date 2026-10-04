"""Storage-only saved research-report workflow; never changes scientific records."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from contextlib import suppress
from uuid import uuid4

from sqlalchemy import select

from ..database import session_scope
from ..experiments.pdf_reports import pdf_report
from ..experiments.reports import report_data
from ..storage.entities import Dataset, Experiment, ResearchEvidencePackage
from ..storage.repository import require
from ..utils.serialization import clean_json, utcnow
from ..utils.errors import AppError
from .auth import SupabasePrincipal
from .gateway import gateway

REPORT_VERSION = "1"


def _source_fingerprint(data: dict) -> str:
    stable = deepcopy(clean_json(data))
    stable.pop("generated_at", None)
    # Database reads may not guarantee list order; snapshot identity must.
    for key in ("models", "interpretation"):
        if isinstance(stable.get(key), list):
            stable[key] = sorted(stable[key], key=lambda item: str(item.get("id") or item.get("model_id") or item) if isinstance(item, dict) else str(item))
    comparison = stable.get("comparison")
    if isinstance(comparison, dict) and isinstance(comparison.get("pairs"), list):
        comparison["pairs"] = sorted(comparison["pairs"], key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _primary_result(models: list[dict]) -> dict | None:
    for metric in ("roc_auc", "f1", "accuracy", "recall", "specificity", "precision"):
        ranked = []
        for model in models:
            value = (model.get("metrics") or {}).get("test", {}).get(metric)
            if isinstance(value, (int, float)):
                ranked.append((float(value), model))
        if ranked:
            value, model = max(ranked, key=lambda item: item[0])
            return {"model": model.get("display_name") or model.get("model_type"), "metric": metric, "value": value}
    return None


def public_record(record: dict, *, already_saved: bool | None = None) -> dict:
    result = {
        "saved_report_id": record.get("id"),
        "title": record.get("report_title"),
        "experiment_id": record.get("experiment_id"),
        "experiment_name": record.get("experiment_name"),
        "dataset_name": record.get("dataset_name"),
        "report_version": record.get("report_version"),
        "evidence_package_id": record.get("evidence_package_id"),
        "evidence_package_fingerprint": record.get("evidence_package_fingerprint"),
        "report_artifact_id": record.get("report_artifact_id"),
        "report_fingerprint": record.get("report_fingerprint"),
        "integrity_hash": record.get("integrity_hash"),
        "generated_at": record.get("generated_at"),
        "saved_at": record.get("saved_at"),
        "size_bytes": record.get("file_size"),
        "content_type": record.get("content_type"),
        "status": record.get("status"),
        "primary_result": record.get("primary_result"),
    }
    if already_saved is not None:
        result["already_saved"] = already_saved
    return result


def list_saved_reports(principal: SupabasePrincipal, experiment_id: str | None = None) -> list[dict]:
    return [public_record(row) for row in gateway.list(principal.user_id, experiment_id=experiment_id)]


def get_saved_report(principal: SupabasePrincipal, saved_report_id: str) -> tuple[dict, dict]:
    record = gateway.get(principal.user_id, saved_report_id)
    if not record:
        raise AppError("saved_report_not_found", "The saved research report was not found.", 404)
    return record, public_record(record)


def save_research_report(principal: SupabasePrincipal, experiment_id: str) -> dict:
    # report_data and pdf_report are the exact 7A source/rendering path. They read
    # existing evidence only and perform no training or scientific recomputation.
    data = report_data(experiment_id)
    report_fingerprint = _source_fingerprint(data)
    existing = gateway.find_existing(principal.user_id, experiment_id, report_fingerprint, REPORT_VERSION)
    if existing:
        return public_record(existing, already_saved=True)

    with session_scope() as session:
        experiment = require(session, Experiment, experiment_id)
        dataset = session.get(Dataset, experiment.dataset_id)
        package = session.scalar(select(ResearchEvidencePackage).where(
            ResearchEvidencePackage.experiment_id == experiment_id
        ).order_by(ResearchEvidencePackage.created_at.desc(), ResearchEvidencePackage.id.desc()))
        snapshot = {
            "experiment_name": experiment.name or f"Experiment {experiment.id[:8]}",
            "dataset_name": dataset.name if dataset else None,
            "evidence_package_id": package.id if package else None,
            "evidence_package_fingerprint": package.package_fingerprint if package else None,
        }

    try:
        pdf = pdf_report(data)
    except Exception as error:
        raise AppError("pdf_generation_failed", "The authoritative PDF could not be generated for saving.", 500) from error

    saved_report_id = str(uuid4())
    saved_at = utcnow().isoformat()
    storage_reference = f"{principal.user_id}/{experiment_id}/{saved_report_id}.pdf"
    integrity_hash = hashlib.sha256(pdf).hexdigest()
    gateway.upload_pdf(storage_reference, pdf)
    record = {
        "id": saved_report_id,
        "owner_user_id": principal.user_id,
        "experiment_id": experiment_id,
        "evidence_package_id": snapshot["evidence_package_id"],
        "evidence_package_fingerprint": snapshot["evidence_package_fingerprint"],
        "report_artifact_id": None,
        "report_fingerprint": report_fingerprint,
        "report_version": REPORT_VERSION,
        "report_title": data.get("title") or "EntangleX Q-Health Research Experiment Report",
        "dataset_name": snapshot["dataset_name"],
        "experiment_name": snapshot["experiment_name"],
        "primary_result": _primary_result(data.get("models") or []),
        "generated_at": data.get("generated_at"),
        "saved_at": saved_at,
        "storage_reference": storage_reference,
        "content_type": "application/pdf",
        "file_size": len(pdf),
        "integrity_hash": integrity_hash,
        "status": "active",
        "created_at": saved_at,
        "updated_at": saved_at,
    }
    try:
        stored = gateway.insert(record)
    except AppError as error:
        # Metadata is authoritative; never retain an unreferenced private upload.
        with suppress(AppError):
            gateway.delete_pdf(storage_reference)
        if error.code == "saved_report_conflict":
            existing = gateway.find_existing(principal.user_id, experiment_id, report_fingerprint, REPORT_VERSION)
            if existing:
                return public_record(existing, already_saved=True)
        raise
    return public_record(stored, already_saved=False)


def download_saved_report(principal: SupabasePrincipal, saved_report_id: str) -> tuple[bytes, dict]:
    record, public = get_saved_report(principal, saved_report_id)
    content = gateway.download_pdf(record["storage_reference"])
    if hashlib.sha256(content).hexdigest() != record.get("integrity_hash"):
        raise AppError("saved_report_integrity_failure", "The saved report failed integrity verification.", 409)
    return content, public


def delete_saved_report(principal: SupabasePrincipal, saved_report_id: str) -> dict:
    # Archiving removes the user-visible saved copy while preserving the canonical
    # experiment, evidence package, models, dataset, and private integrity trail.
    record, _ = get_saved_report(principal, saved_report_id)
    archived = gateway.archive(principal.user_id, saved_report_id, utcnow().isoformat())
    if not archived:
        raise AppError("saved_report_not_found", "The saved research report was not found.", 404)
    return {"saved_report_id": record["id"], "status": "deleted"}
