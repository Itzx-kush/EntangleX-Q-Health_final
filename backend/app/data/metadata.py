"""Deterministic metadata suggestions for dataset inspection.

This module deliberately uses only the filename, parsed dataframe metadata, and
curated catalog values. It never calls an external model or remote service.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_POSITIVE_WORDS = {"positive", "pos", "disease", "diseased", "malignant", "present", "true", "yes"}
_NEGATIVE_WORDS = {"negative", "neg", "healthy", "benign", "absent", "false", "no"}


def _readable_name(filename: str) -> str:
    stem = Path(filename or "").stem
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.title() if stem else "Uploaded Biomedical Dataset"


def _filename_version(filename: str) -> str | None:
    stem = Path(filename or "").stem
    match = re.search(r"(?:^|[ _-])(?:version[ _-]?)?v(\d+(?:\.\d+)?)\b", stem, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"(?:^|[ _-])version[ _-]?(\d+(?:\.\d+)?)\b", stem, flags=re.IGNORECASE)
    return f"v{match.group(1)}" if match else None


def _infer_domain(filename: str, target: str | None) -> tuple[str, str]:
    text = f"{Path(filename or '').stem} {target or ''}".lower()
    keyword_groups = (
        ("oncology", ("breast", "cancer", "carcinoma", "tumor", "tumour", "malignant")),
        ("cardiovascular", ("heart", "cardiac", "cardio", "coronary", "hypertension")),
        ("endocrinology", ("diabetes", "diabetic", "glucose", "insulin", "pima")),
        ("neurology", ("neuro", "alzheimer", "parkinson", "stroke")),
    )
    for domain, keywords in keyword_groups:
        if any(keyword in text for keyword in keywords):
            return domain, "filename_keyword"
    return "biomedical", "fallback_biomedical"


def _class_info(distribution: dict[str, int]) -> tuple[list[str], dict[str, int]]:
    filtered = {str(label): int(count) for label, count in distribution.items() if str(label) != "<missing>"}
    return list(filtered), filtered


def _positive_rule(classes: list[str]) -> tuple[str | None, float, str, str | None]:
    if len(classes) != 2:
        return None, 0.0, "binary_target_required", "A positive-class suggestion is only available for exactly two observed classes."
    normalized = {label: re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") for label in classes}
    if set(normalized.values()) == {"0", "1"}:
        return next(label for label in classes if normalized[label] == "1"), 0.95, "binary_numeric_rule", None
    positive = [label for label in classes if normalized[label] in _POSITIVE_WORDS]
    negative = [label for label in classes if normalized[label] in _NEGATIVE_WORDS]
    if len(positive) == 1 and len(negative) == 1:
        return positive[0], 0.95, "semantic_label_rule", None
    return None, 0.0, "ambiguous_binary_labels", "The two observed classes do not identify a defensible positive class; confirm it explicitly."


def suggest_metadata(
    filename: str,
    inspection: dict[str, Any],
    *,
    content_hash: str | None = None,
    catalog: dict[str, Any] | None = None,
    selected_target: str | None = None,
    selected_positive: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    candidates = inspection.get("target_candidates") or []
    candidate = None
    if selected_target:
        candidate = next((item for item in candidates if item.get("column") == selected_target), None)
    if candidate is None and candidates:
        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        clear = float(top.get("confidence", 0)) >= 0.8 and (second is None or float(top.get("confidence", 0)) - float(second.get("confidence", 0)) >= 0.15)
        candidate = top if clear else None
        if not clear:
            warnings.append("Target detection is ambiguous; choose and confirm a target column.")
    target = selected_target or (candidate.get("column") if candidate else None)
    target_confidence = float(candidate.get("confidence", 0.0)) if candidate else 0.0
    target_source = "user_selected" if selected_target else ("inspection.target_candidates[0]" if candidate else "inspection.target_candidates")

    distribution = (candidate or {}).get("class_distribution") or inspection.get("class_distribution") or {}
    classes, counts = _class_info(distribution)
    target_classes_source = "target_column_values" if selected_target else ("inspection.target_candidates[0].class_distribution" if candidate else "inspection.target_candidates")
    positive = selected_positive
    positive_confidence = 1.0 if selected_positive else 0.0
    positive_source = "user_selected" if selected_positive else "ambiguous_binary_labels"
    positive_warning = None
    if not positive:
        positive, positive_confidence, positive_source, positive_warning = _positive_rule(classes)
    if positive_warning:
        warnings.append(positive_warning)
    negative = next((label for label in classes if label != positive), None) if positive else None

    if catalog:
        name = str(catalog["name"])
        name_source = "catalog"
        target = str(catalog["target"])
        target_confidence = 1.0
        target_source = "catalog"
        target_classes_source = "catalog"
        classes = [str(catalog["positive_label"]), str(catalog["negative_label"])]
        counts = {str(label): int(count) for label, count in (inspection.get("class_distribution") or {}).items()}
        positive = str(catalog["positive_label"])
        positive_confidence = 1.0
        positive_source = "catalog"
        negative = str(catalog["negative_label"])
        version = str(catalog["version"])
        version_source = "catalog"
        domain = str(catalog["domain"])
        domain_source = "catalog"
        source = str(catalog["source"])
        source_source = "catalog"
    else:
        name = _readable_name(filename)
        name_source = "filename"
        version_from_filename = _filename_version(filename)
        if version_from_filename:
            version, version_source = version_from_filename, "filename"
        else:
            snapshot = (content_hash or "unknown")[:12]
            version, version_source = f"upload-snapshot-{snapshot}", "generated_snapshot"
            warnings.append("No authoritative version was provided; this is a platform-generated snapshot identifier.")
        domain, domain_source = _infer_domain(filename, target)
        source, source_source = "User-provided", "default_user_upload"

    if len(classes) != 2 and target:
        warnings.append("Observed target classes are not binary; the current Q-Health research workflow will block registration.")
    if target is None:
        warnings.append("No high-confidence target was detected; select one before compatibility analysis.")
    if positive is None and len(classes) == 2:
        warnings.append("Positive class is intentionally left unset because the binary labels are ambiguous.")
    if positive and negative is None and len(classes) == 2:
        negative = next((label for label in classes if label != positive), None)

    suggestions = {
        "name": name,
        "name_source": name_source,
        "target": target,
        "target_confidence": round(target_confidence, 2),
        "target_source": target_source,
        "target_classes": classes,
        "target_classes_source": target_classes_source,
        "target_class_distribution": counts,
        "positive_label": positive,
        "positive_label_confidence": round(positive_confidence, 2),
        "positive_label_source": positive_source,
        "negative_label": negative,
        "negative_label_source": "remaining_binary_class" if negative else None,
        "version": version,
        "version_source": version_source,
        "domain": domain,
        "domain_source": domain_source,
        "source": source,
        "source_source": source_source,
    }
    return suggestions, list(dict.fromkeys(warnings))
