# Controlled Classical-vs-Quantum Comparison Protocol

## Scientific purpose

The controlled comparison protocol formalizes the repository's existing pairwise comparison and fairness evidence. It determines whether persisted classical and quantum-family model records were evaluated under sufficiently matched experimental conditions. It does not retrain models, alter artifacts, tune thresholds, rank models, or declare quantum advantage.

**A controlled comparison demonstrates experimental matching under the persisted protocol. It does not establish clinical validity, statistical superiority, or quantum computational advantage.**

Schema version: `controlled_comparison_protocol_v1`.

## Architecture

The protocol reuses `Experiment`, `Run`, `ModelRecord`, `DatasetVersion`, `ConditionTask`, threshold/calibration studies, robustness records, multi-seed studies, quantum diagnostics, provider provenance, and immutable `Artifact` records. An experiment may have an N × M matrix of classical and quantum-family pairs.

`ControlledComparisonProtocol` persists:

- model roles and pair identities;
- tri-state control checks (`PASS`, `FAIL`, `UNKNOWN`);
- protocol and configuration fingerprints;
- pair and overall status;
- safe evidence references, limitations, and provenance;
- an immutable `controlled_comparison_protocol` artifact.

Repeated execution with unchanged persisted evidence is idempotent.

## Required controls

Each pair checks dataset/version/hash, target and label semantics, sample-pool identity, train/test population fingerprints, split identity, sample budget, randomization/CV policy, preprocessing, common representation, PCA, angle scaling, grouping, threshold policy and lock provenance, and calibration policy.

Raw row values and patient/group identifiers are never persisted. Row/group identity is represented with fingerprints and aggregate counts only.

Model architecture, optimizer, ansatz, quantum layers, feature map, and other model-specific variables are documented as intentional differences rather than control failures.

## Status semantics

- `CONTROLLED`: all required controls pass.
- `CONTROLLED_WITH_LIMITATIONS`: all required controls pass while non-blocking timing, robustness, multi-seed, calibration, or diagnostic evidence is incomplete.
- `NOT_CONTROLLED`: at least one required control fails.
- `INCOMPLETE_EVIDENCE`: a required control cannot be established.
- `BLOCKED`: the requested pair matrix cannot be evaluated.

These states describe experimental control, not model quality.

## Threshold and calibration

Threshold controls compare the selection policy and target, not the numerical thresholds. A frozen threshold must have persisted provenance before final holdout evaluation. The final holdout is never used by protocol generation.

Calibration configuration and associated study references are recorded. A mismatch is visible and is never silently corrected.

## Common representation

The protocol separates the common pre-model representation—input features, preprocessing, feature selection, PCA, and angle scaling—from quantum encoding and model execution. Classical models are not required to use a quantum circuit.

## Quantum provenance

Persisted provider/backend identity, execution mode, capability evidence, configuration fingerprint, logical resources, shots/noise, diagnostics, and `real_hardware` are allowlisted. Missing provenance remains missing. Simulator timing is explicitly not QPU runtime.

## API

- `POST /api/experiments/{id}/controlled-comparison/preflight` — non-mutating checks
- `POST /api/experiments/{id}/controlled-comparison` — idempotently persist protocol and artifact
- `GET /api/experiments/{id}/controlled-comparison` — latest protocol
- `GET /api/experiments/{id}/controlled-comparison/{protocol_id}` — exact protocol
- `GET /api/experiments/{id}/controlled-comparison/{protocol_id}/provenance` — compact provenance

The existing `GET /api/experiments/{id}/comparison` remains backward compatible and gains `controlled_protocol` and `controlled_protocol_pair`. `controlled_benchmarks` contains only pairs verified by a persisted protocol. Legacy comparisons remain readable but are not promoted to controlled status.

## Reproducibility and non-claims

The protocol fingerprint covers pair identities and every emitted control/evidence field. Performance deltas retain the explicit direction `quantum − classical`. No winner, best-model label, overall score, clinical claim, or quantum-advantage claim is produced.