# Pipeline Version Registry

## Purpose

The Pipeline Version Registry identifies the exact computational definition used by an EntangleX Q-Health experiment. It records ordered stages, safe configuration metadata, immutable references, lifecycle state, and a deterministic fingerprint.

Pipeline versions identify computational definitions. They do not establish model quality, scientific validity, clinical validity, or scientific superiority.

## Data model

- **Pipeline Definition** is a named family such as `Q-Health Experiment Pipeline`.
- **Pipeline Version** is one fingerprinted definition in that family. It has a version label, schema version, lifecycle state, optional parent version, and canonical definition.
- **Pipeline Stage** is an ordered stage snapshot with a type, name, component version, safe configuration, and fingerprint.

Pipeline versions reference existing dataset versions, controlled-comparison protocols, artifacts, experiments, and runs by identifier. They do not duplicate model records, dataset contents, evidence, or artifacts.

## Canonical stages

Supported stage types are:

1. data validation
2. preprocessing
3. feature engineering
4. representation
5. optional quantum encoding
6. model
7. evaluation

Classical and quantum configurations use the same registry. Quantum definitions record encoding and provider-facing configuration already present in the validated experiment configuration; they do not claim hardware execution. Stage positions must be unique, contiguous, and start at one.

## Version semantics and lifecycle

Versions use the lifecycle states `DRAFT`, `ACTIVE`, `DEPRECATED`, and `ARCHIVED`. Status describes lifecycle only.

A draft is validated before publication. Publication canonicalizes and fingerprints the definition, then freezes it. Published versions and versions referenced by experiments cannot be modified. A computational change requires a new version. A new version may reference its parent with `parent_pipeline_version_id`.

Reruns retain the exact version when their computational definition is unchanged. Selecting another version is explicit and must match the submitted experiment configuration. The registry never resolves an experiment to “latest.”

## Deterministic fingerprint

`definition_fingerprint` is SHA-256 over the canonical definition. Canonicalization normalizes object-key ordering, strings, nulls, and numeric representations while preserving semantically ordered lists such as pipeline stages and feature order. It excludes timestamps, database row order, lifecycle state, descriptions, and other presentation metadata.

Each stage has a separate deterministic fingerprint. Equivalent canonical definitions reuse the existing version rather than creating duplicate immutable identities.

## Validation and preflight

Preflight reports:

- structural definition validity;
- referenced-object validity;
- deterministic fingerprint verification;
- required-stage coverage; and
- whether the draft is publishable.

Diagnostics are structured blockers and warnings, not a quality score. Secret-like keys, credentials, raw data, excessive nesting, malformed stage order, unsupported stage types, and invalid references are rejected.

## Experiment and reproducibility integration

New experiments and runs store `pipeline_version_id`. Before enqueue, the validated training configuration is converted to a canonical definition or matched to an explicitly selected active version. The execution manifest records the version ID and fingerprint. Experiment reports expose the same identity.

Legacy experiments remain readable. If no deterministic version was recorded, `GET /api/experiments/{id}/pipeline` returns `LEGACY_UNRESOLVED`; the system does not fabricate a historical version.

## Lineage and evidence integration

The existing lineage service represents:

- Pipeline Definition → Pipeline Version;
- parent Pipeline Version → derived Pipeline Version;
- Dataset Version → Pipeline Version;
- Pipeline Version → Experiment / Run;
- Pipeline Version → Controlled Comparison Protocol; and
- Pipeline Version → ordered stages.

Research Evidence Packages and Model Cards include pipeline identity by reference where it exists. Their evidence and card content remain authoritative in their own systems.

## API

- `GET /api/pipelines` — list versions and usage.
- `POST /api/pipelines/preflight` — validate a candidate.
- `POST /api/pipelines` — create or reuse a draft version.
- `GET /api/pipelines/{id}` — inspect one version.
- `GET /api/pipelines/{id}/preflight` — preflight a stored version.
- `POST /api/pipelines/{id}/publish` — validate and freeze a draft.
- `GET /api/pipelines/{id}/diff/{other_id}` — structured neutral differences.
- `GET /api/experiments/{id}/pipeline` — exact experiment binding or legacy state.

The diff reports `Added`, `Removed`, `Changed`, and `Unchanged`. It does not rank versions.

## Frontend

Experiment Detail contains a Pipeline Version panel with lifecycle, version identity, fingerprint, usage, publication time, ordered stages, canonical definition, and an optional version comparison. Legacy, loading, and API-error states are explicit. The panel is lazy and does not expand registry payloads into ordinary experiment-list responses.

## Migration and compatibility

The additive migration creates the three registry tables, adds nullable pipeline references to experiments and runs, and installs traversal and lookup indexes. Existing rows are not rewritten. Existing report, verified-demo, evidence, Model Card, controlled comparison, lineage, and experiment APIs remain compatible.

## Privacy and security

Definitions contain computational metadata and object references only. Raw biomedical rows, CSV content, patient identifiers, credentials, tokens, passwords, secrets, and private storage paths are prohibited. Public payloads expose safe references and fingerprints rather than artifact contents.

## Limitations

- Historical experiments without an exact persisted mapping remain unresolved.
- The registry describes a specification; it is not a workflow orchestrator or experiment runner.
- Structural validation does not prove scientific appropriateness.
- Cross-version diff identifies definition changes, not their scientific effect.
- Provider and protocol records remain authoritative in their existing registries.