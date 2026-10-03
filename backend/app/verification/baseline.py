"""Stable Scientific CI baseline metadata.

This module is the reviewable record of the scientific contracts Scientific CI
protects.  It intentionally stores a small number of canonical fixture
fingerprints so that an unintended change to canonical serialization, to a
definition schema or to a scientific identity computation fails CI loudly
instead of silently rewriting scientific history.

Why storing fingerprints is safe here: every value below is derived from a
canonical synthetic fixture in ``app/verification/fixtures.py`` with a fixed
seed and no runtime, clock, identity or environment input.  When a scientific
identity genuinely changes, the change must be reviewed and this baseline must
be updated in the same pull request.
"""

from __future__ import annotations

# Live module constants that Scientific CI compares against the repository's
# scientific schema versions.  A mismatch fails the schema-contract check.
SCHEMA_VERSIONS: dict[str, str] = {
    "research_evidence_package": "research_evidence_package_v1",
    "deep_experiment_lineage": "deep_experiment_lineage_v1",
    "pipeline_definition": "pipeline_definition_v1",
    "protocol_definition": "protocol_definition_v1",
    "scientific_audit_event": "scientific_audit_event_v1",
    "dataset_quality_scorecard": "dataset_quality_scorecard_v1",
    "model_card": "model_card_v1",
    "controlled_comparison_protocol": "controlled_comparison_protocol_v1",
    "run_manifest": "1.0.0",
    "subgroup_analysis": "subgroup_analysis_v1",
}

# The reviewed set of required checks.  Adding or removing a required check is a
# reviewable change to the Scientific CI contract and must update this list.
REQUIRED_CHECK_IDS: tuple[str, ...] = (
    "application_import",
    "application_startup_lifespan",
    "artifact_immutability",
    "artifact_registry_contract",
    "audit_event_immutability",
    "audit_timeline_contract",
    "controlled_comparison_contract",
    "database_migration_upgrade_path",
    "database_schema_contract",
    "dataset_quality_contract",
    "deployment_import_safety",
    "evidence_package_contract",
    "experiment_integrity",
    "fingerprint_canonicalization",
    "fingerprint_cross_process_determinism",
    "fingerprint_determinism_matrix",
    "legacy_compatibility",
    "lineage_cycle_and_relationship_protection",
    "lineage_integrity",
    "lineage_relationship_immutability",
    "model_card_contract",
    "pipeline_registry_contract",
    "pipeline_version_immutability",
    "privacy_and_secret_safety",
    "protocol_attachment_and_compliance",
    "protocol_registry_contract",
    "protocol_version_immutability",
    "quantum_diagnostics_contract",
    "quantum_provider_contract",
    "reproducibility_manifest_contract",
    "scientific_schema_contracts",
    "subgroup_contract",
    "verification_registry_contract",
    "verification_result_contract",
)

# Canonical fixture fingerprints.  Generated from the fixtures with
# ``python -m app.verification --print-baseline`` and reviewed by hand.
BASELINE_EXPECTATIONS: dict[str, str] = {
    "canonical_json": "2e7bd2a925ddaa46b84223bed8d2749a1d67038f0d03873a326063f3ce4dc9b8",
    "reproducibility_manifest": "741531d2a12427b43411811a21c4685d967f72f9191ddfbce50d83972878b9c3",
    "pipeline_definition": "97308e525acb1819b0561cef40762ffe0c06e79702e1f9e078701aa640d7bb15",
    "protocol_definition": "86bc8060074af96bd6276c3d46ccc14d04ae6e685c9a8a1dc326dfbcaa064054",
    "subgroup_study": "34337ee865fd11e204a11a002ab919b633833bf9b27640afb32144d2cdd08100",
    "dataset_quality_scorecard": "a4cacfb33090f826fc84f0d11d13010dd73829afbddfa34d9a27ea5ef6efd099",
    "scientific_audit_event": "0a818eb7162bda6b720cc3ac1e45ff8329d7acb2f51a9184250e5ffd61a01556",
    "quantum_circuit": "473553459296879ac84604102bc7fefaa71cccfa42dd2cd433f2a8d20c4b41d6",
    "controlled_comparison_index": "bf8258e4647d5adc206f6ecbd1ef443defc4345bc2edb2cf412382e7e18db394",
}
