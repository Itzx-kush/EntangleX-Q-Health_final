"""Biomedical Subgroup Analysis verification (Prompt 18).

Deterministic synthetic fixtures only.  The checks protect the scientific
semantics that are easy to regress: an undefined single-class metric must stay
UNDEFINED (never zero), undersized cohorts must be withheld, missing subgroup
values must follow the declared policy, and no patient-level payload may reach
an aggregate response.
"""

from __future__ import annotations

import numpy as np

from ..fixtures import (
    SUBGROUP_FIELD,
    canonical_subgroup_study_fields,
    stratified_metric_arrays,
    synthetic_biomedical_frame,
)
from ..isolation import initialize_database
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import flatten_strings, require_fingerprint

METRIC_STATUSES = {"AVAILABLE", "UNDEFINED", "INSUFFICIENT_DATA", "WITHHELD", "NOT_APPLICABLE", "UNVERIFIABLE"}


@check(
    check_id="subgroup_contract",
    name="Subgroup analysis contract",
    category=CheckCategory.EXPERIMENT_INTEGRITY,
    description="Undefined-metric semantics, minimum-group safeguards, missing-value policy, deterministic metrics and study fingerprints.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def subgroup_contract() -> CheckResult:
    from app.subgroups.schemas import SubgroupAnalysisRequest, SubgroupRule
    from app.subgroups.service import (
        calculate_stratified_metrics,
        compute_study_fingerprint,
        derive_predefined_rules,
        evaluate_subgroup_mask,
    )

    initialize_database()
    problems: list[str] = []
    labels, predictions, scores = stratified_metric_arrays()

    first = calculate_stratified_metrics(labels, predictions, scores, scores, 10)
    second = calculate_stratified_metrics(labels, predictions, scores, scores, 10)
    if {key: value.model_dump() for key, value in first.items()} != {
        key: value.model_dump() for key, value in second.items()
    }:
        problems.append("stratified metrics are not deterministic for identical input")
    for name, metric in first.items():
        if metric.status not in METRIC_STATUSES:
            problems.append(f"metric {name} reported an unknown status {metric.status!r}")
    if first["accuracy"].status != "AVAILABLE" or first["accuracy"].ci_lower is None:
        problems.append("a well-populated cohort did not report an available accuracy metric with a confidence interval")

    single_class = np.ones_like(labels)
    undefined = calculate_stratified_metrics(single_class, predictions, scores, scores, 10)
    for metric_name in ("roc_auc", "pr_auc"):
        metric = undefined[metric_name]
        if metric.status != "UNDEFINED":
            problems.append(
                f"a single-class subgroup reported {metric_name} as {metric.status!r} instead of UNDEFINED"
            )
        if metric.value is not None:
            problems.append(f"a single-class subgroup reported a numeric {metric_name} value ({metric.value})")
        if "single observed target class" not in (metric.reason or ""):
            problems.append(f"the {metric_name} undefined reason does not explain the single-class cause")

    withheld = calculate_stratified_metrics(labels[:5], predictions[:5], scores[:5], scores[:5], 20)
    for name, metric in withheld.items():
        if metric.status != "WITHHELD" or metric.value is not None:
            problems.append(f"an undersized cohort reported {name} as {metric.status!r} with value {metric.value}")
            break
    if "minimum_n" not in (withheld["accuracy"].reason or ""):
        problems.append("the withheld reason does not reference the minimum_n safeguard")

    frame = synthetic_biomedical_frame()
    frame.loc[0:5, SUBGROUP_FIELD] = np.nan
    series = frame[SUBGROUP_FIELD]
    rule = SubgroupRule(id="younger", label="Younger adults", field=SUBGROUP_FIELD, operator="less_than", value=50)
    excluded = evaluate_subgroup_mask(series, rule)
    if bool(excluded[0]):
        problems.append("a rule-based subgroup mask included a row whose subgroup field is missing")
    if len(excluded) != len(series):
        problems.append("the subgroup mask does not cover every row of the dataset")
    missing_rule = SubgroupRule(id="unknown", label="Unknown subgroup value", field=SUBGROUP_FIELD, operator="is_null")
    unknown = evaluate_subgroup_mask(series, missing_rule)
    if not bool(unknown[0]) or int(unknown.sum()) != 6:
        problems.append("the is_null subgroup rule does not isolate rows with missing subgroup values")
    try:
        SubgroupAnalysisRequest(subgroup_field=SUBGROUP_FIELD, missing_value_policy="separate_unknown_group")
    except Exception:
        problems.append("the separate_unknown_group missing-value policy is no longer accepted")
    try:
        SubgroupAnalysisRequest(subgroup_field=SUBGROUP_FIELD, missing_value_policy="not_a_policy")
        problems.append("an invalid missing-value policy was accepted")
    except Exception:
        pass

    rules = derive_predefined_rules(frame, SUBGROUP_FIELD)
    if not rules:
        problems.append("predefined subgroup rules were not derived for a numeric field")
    for derived in rules:
        if derived.field != SUBGROUP_FIELD:
            problems.append("a derived subgroup rule targets an unexpected field")

    fields = canonical_subgroup_study_fields()
    study_fingerprint = require_fingerprint(
        compute_study_fingerprint(
            fields["experiment_id"],
            fields["model_id"],
            fields["dataset_hash"],
            fields["subgroup_field"],
            [SubgroupRule(**rule) for rule in fields["rules"]],
            fields["minimum_n"],
            fields["missing_value_policy"],
            fields["reference_subgroup_id"],
        ),
        label="subgroup study fingerprint",
    )
    reordered = [SubgroupRule(**rule) for rule in reversed(fields["rules"])]
    reordered_fingerprint = compute_study_fingerprint(
        fields["experiment_id"],
        fields["model_id"],
        fields["dataset_hash"],
        fields["subgroup_field"],
        reordered,
        fields["minimum_n"],
        fields["missing_value_policy"],
        fields["reference_subgroup_id"],
    )
    if reordered_fingerprint != study_fingerprint:
        problems.append("subgroup study fingerprint depends on rule declaration order")
    changed_fingerprint = compute_study_fingerprint(
        fields["experiment_id"],
        fields["model_id"],
        fields["dataset_hash"],
        fields["subgroup_field"],
        [SubgroupRule(**rule) for rule in fields["rules"]],
        fields["minimum_n"] + 5,
        fields["missing_value_policy"],
        fields["reference_subgroup_id"],
    )
    if changed_fingerprint == study_fingerprint:
        problems.append("changing the minimum group size did not change the study fingerprint")

    serialized = flatten_strings({name: metric.model_dump() for name, metric in first.items()})
    for forbidden in ("patient_id", "mrn", "raw_rows", "observed_class"):
        if forbidden in serialized:
            problems.append(f"aggregate metric payload exposes {forbidden!r}")

    from app.storage.entities import SubgroupAnalysisStudy

    required_columns = {
        "definition_fingerprint",
        "subgroup_field",
        "configuration",
        "overall_population",
        "subgroups_results",
        "comparisons",
        "limitations",
        "provenance",
    }
    declared_columns = set(SubgroupAnalysisStudy.__table__.columns.keys())
    missing_columns = sorted(required_columns - declared_columns)
    if missing_columns:
        problems.append(f"the subgroup study record no longer exposes: {missing_columns}")

    if problems:
        return CheckResult(
            check_id="subgroup_contract",
            category=CheckCategory.EXPERIMENT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="undefined metrics stay UNDEFINED, safeguards withhold small cohorts and aggregate output stays private",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="subgroup_contract",
        category=CheckCategory.EXPERIMENT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Subgroup semantics hold: undefined metrics stay UNDEFINED, small cohorts are withheld and output is aggregate-only.",
        evidence={
            "study_fingerprint": study_fingerprint,
            "rule_order_independent": True,
            "single_class_metrics": {
                name: undefined[name].status for name in ("roc_auc", "pr_auc")
            },
            "withheld_metric_status": withheld["accuracy"].status,
            "derived_rule_count": len(rules),
            "missing_value_handling": "excluded from rule-based groups, isolatable with is_null",
            "study_columns": sorted(required_columns),
        },
    )
