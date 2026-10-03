"""Model Card verification (Prompt 11).

Model cards must generate deterministically from persisted evidence, keep their
required sections, resolve their references and never leak raw payloads.  Model
quality and model ranking are explicitly out of scope for CI.
"""

from __future__ import annotations

from ..fixtures import persist_chain
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import flatten_strings

REQUIRED_SECTIONS = (
    "schema_version",
    "card_status",
    "model_identity",
    "model",
    "task",
    "data",
    "training",
    "evaluation",
    "reproducibility",
    "calibration",
    "threshold",
    "external_validation",
    "distribution_shift",
    "multi_seed_evidence",
    "quantum",
    "provenance",
    "limitations",
)


@check(
    check_id="model_card_contract",
    name="Model card contract",
    category=CheckCategory.MODEL_CARD_INTEGRITY,
    description="Deterministic card generation, required sections, resolved references, idempotent artifact and payload privacy.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=240.0,
)
def model_card_contract() -> CheckResult:
    from app.model_cards.service import MODEL_CARD_SCHEMA_VERSION, assemble_card, get_or_create_card
    from app.storage.entities import Artifact, Dataset, Experiment, ModelRecord

    initialize_database()
    chain = persist_chain(with_pipeline=True, with_protocol=True)
    problems: list[str] = []

    with session() as scope:
        first, _source, _payload = assemble_card(scope, chain.model_id)
        second, _source2, _payload2 = assemble_card(scope, chain.model_id)
        _card, first_artifact = get_or_create_card(scope, chain.model_id)
        _card2, second_artifact = get_or_create_card(scope, chain.model_id)
        artifact_count = scope.query(Artifact).filter(
            Artifact.model_id == chain.model_id, Artifact.artifact_type == "model_card"
        ).count()
        model = scope.get(ModelRecord, chain.model_id)
        experiment = scope.get(Experiment, chain.experiment_id)
        dataset = scope.get(Dataset, chain.dataset_id)

    if first != second:
        problems.append("model card generation is not deterministic for unchanged evidence")
    if first.get("schema_version") != MODEL_CARD_SCHEMA_VERSION:
        problems.append("model card reports an unexpected schema version")
    missing = sorted(section for section in REQUIRED_SECTIONS if section not in first)
    if missing:
        problems.append(f"model card is missing required sections: {missing}")
    if first.get("model_identity", {}).get("model_id") != chain.model_id:
        problems.append("model card identity does not reference the requested model")
    if first.get("model_identity", {}).get("experiment_id") != experiment.id:
        problems.append("model card identity does not reference the model's experiment")
    if first.get("data", {}).get("dataset_id") != dataset.id:
        problems.append("model card dataset reference does not resolve to the persisted dataset")
    if model.status != "ready":
        problems.append("the synthetic model is not in a ready state for card generation")
    for section in ("calibration", "threshold", "external_validation", "distribution_shift", "multi_seed_evidence"):
        if first[section].get("status") != "not_available":
            problems.append(f"model card section {section} did not report missing evidence honestly")
    if first_artifact is None or second_artifact is None:
        problems.append("model card generation did not return an artifact")
    elif first_artifact.id != second_artifact.id or first_artifact.integrity_hash != second_artifact.integrity_hash:
        problems.append("model card artifact is not idempotent for unchanged evidence")
    if artifact_count != 1:
        problems.append(f"expected exactly one model card artifact, found {artifact_count}")

    text = flatten_strings(first).lower()
    for forbidden in ("patient_id", "raw_patient_rows", "api_key", "password"):
        if forbidden in text:
            problems.append(f"model card exposes the prohibited term {forbidden!r}")
    if "superior" in text or "best model" in text:
        problems.append("model card contains comparative superiority language")

    if problems:
        return CheckResult(
            check_id="model_card_contract",
            category=CheckCategory.MODEL_CARD_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="deterministic, complete, reference-resolving and privacy-safe model cards",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="model_card_contract",
        category=CheckCategory.MODEL_CARD_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Model cards generate deterministically, keep their required sections and resolve their references.",
        evidence={
            "schema_version": MODEL_CARD_SCHEMA_VERSION,
            "card_status": first.get("card_status"),
            "section_count": len(REQUIRED_SECTIONS),
            "artifact_id": first_artifact.id,
            "missing_evidence_sections": ["calibration", "threshold", "external_validation", "distribution_shift"],
        },
    )
