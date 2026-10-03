# Deep Experiment Lineage and Provenance

## Purpose and scientific meaning

Deep Experiment Lineage records where persisted research objects came from and
what was subsequently derived from them. It provides a deterministic graph over
the existing experiment registry, dataset versions, executions, models,
artifacts, evidence studies, comparison protocols, Model Card artifacts, and
Research Evidence Packages.

Lineage records provenance metadata. It does **not** establish scientific
validity, causality, model quality, clinical utility, deployment readiness, or
quantum advantage.

## Architecture

The implementation uses the existing relational SQLite database. It does not
introduce a graph database, message broker, or second registry.

Two additive tables provide first-class capture:

- `lineage_nodes` stores immutable references to existing objects.
- `lineage_edges` stores append-only relationships between those references.

The referenced scientific object remains canonical. A lineage node does not
copy a model, study, artifact, report, or evidence package.

Newly created supported objects are captured automatically by a SQLAlchemy
session hook after their normal persistence flush. The hook inserts
deterministic nodes and edges with conflict-safe, append-only semantics.
Normal lineage APIs are read-only.

## Node model

Each node contains:

- deterministic lineage node ID
- object type and canonical object ID
- lineage schema version
- immutable reference fingerprint when available
- small, safe reference metadata
- recorded timestamp

Supported objects include datasets, dataset versions, experiments, runs, jobs,
checkpoints, execution units, model records, artifacts, evidence studies,
controlled-comparison protocols, explanations, and Research Evidence Packages.

Model Cards are represented by their canonical immutable `model_card` Artifact
node. Their payload is not duplicated.

## Edge model and supported relationships

Each edge contains:

- deterministic edge ID
- source and target node IDs
- supported relationship type
- schema version
- deterministic relationship fingerprint
- recorded timestamp
- safe explanatory metadata
- immutable flag

Supported relationships follow explicit persisted foreign keys and identifiers:

- `has_version`: dataset → dataset version
- `selected_by`: dataset/version → experiment, run, model, or study
- `rerun_of`: parent experiment → rerun experiment
- `produced_run`: experiment/study → run
- `scheduled_as`: experiment/run/study → job
- `checkpointed_as`: job → checkpoint
- `executed_unit`: job → execution unit
- `produced_model`: experiment/run → model record
- `has_evidence`: experiment/run/model/study → persisted evidence
- `produced_experiment`: ablation study → derived experiment
- `produced_artifact` and `documented_by`: producer/model → Artifact
- `packaged_as`: experiment → Research Evidence Package
- `included_in`: referenced Artifact/evidence → package
- `represented_by`: package → its immutable package Artifact

No relationship is inferred from timestamps or visual proximity.

## Historical and legacy experiments

Existing deployments predate the lineage tables. Their safe relationships are
reconstructed at read time only from explicit persisted identifiers, such as:

- `Experiment.dataset_id`
- configured `dataset_version_id`
- `Experiment.parent_id`
- `Run.experiment_id`
- `ModelRecord.run_id`
- study model/experiment/artifact references

Reconstructed edges are marked `legacy_reconstructed`, and the snapshot is
`PARTIAL`. Missing parentage is never guessed. Missing referenced objects are
reported as `LEGACY_UNRESOLVED`, not as a model failure.

Verified demonstrations are handled the same way: only installed immutable
package identifiers and explicit stored references are represented. No fake
Run or historical execution is created, and the existing verified-evidence
endpoint remains unchanged.

## Deterministic lineage fingerprint

Schema version: `deep_experiment_lineage_v1`.

The lineage fingerprint is SHA-256 over canonical JSON containing sorted:

- node IDs, object types, canonical object IDs, and immutable fingerprints
- edge source/target IDs, relationship types, and relationship fingerprints

Presentation labels, UI state, traversal timestamps, and other volatile fields
are excluded. The same persisted provenance and query scope produce the same
fingerprint.

## Integrity and immutability

Lineage preflight reports:

- missing references
- orphaned persisted edges
- unsupported or invalid edge types
- duplicate relationships
- captured/current fingerprint mismatches
- cycles
- legacy reconstructed edges
- bounded traversal truncation

Historical edges are not updated or redirected. Re-recording the same
relationship is idempotent. Attempting to change its meaning returns
`immutable_lineage_conflict`. Internal relationship creation rejects unsupported
types and detects a path that would create a cycle, returning
`cyclic_provenance_relationship`.

Snapshot states:

- `COMPLETE`: captured references are consistent for the requested scope.
- `PARTIAL`: explicit legacy relationships were reconstructed or traversal was
  bounded.
- `LEGACY_UNRESOLVED`: one or more explicitly referenced objects are missing.
- `INTEGRITY_REVIEW`: cycles, invalid edges, duplicates, or fingerprint
  mismatches require review.

These states are traceability diagnostics, not quality scores.

## Traversal

The lineage API supports `ancestors`, `descendants`, and `both`. For `both`,
ancestor and descendant traversals are performed independently and then merged;
this prevents a shared dataset ancestor from pulling unrelated sibling
experiments into the graph.

Depth accepts `1` through `12`, or `all`. `all` remains bounded to 12 levels and
500 nodes. Graph construction bulk-loads supported tables and performs
in-memory bounded traversal, avoiding per-node N+1 database queries.

## API

Read-only endpoints:

- `GET /api/experiments/{id}/lineage`
- `GET /api/experiments/{id}/lineage/ancestors`
- `GET /api/experiments/{id}/lineage/descendants`
- `GET /api/experiments/{id}/lineage/preflight`

Main query parameters:

- `depth=1|2|...|12|all`
- `direction=ancestors|descendants|both`
- `include_artifacts=true|false`
- `include_evidence=true|false`

The snapshot returns experiment identity, schema version, status, deterministic
fingerprint, roots, nodes, edges, summary, integrity diagnostics, and explicit
limitations.

Invalid traversal options return the project-standard safe 422 response.
Missing or archived experiments use existing 404/410 conventions. No endpoint
accepts arbitrary user-authored lineage mutations.

## Relationship to existing systems

### Research Evidence Packages

An evidence package appears as a node referenced by package ID and package
fingerprint. Its immutable metadata Artifact and referenced artifact IDs are
connected without copying package contents. Evidence packaging and lineage
remain separate responsibilities.

### Model Cards

The existing Model Card Artifact is connected to its Model Record with
`documented_by`. Lineage does not generate or duplicate Model Cards.

### Controlled Classical-vs-Quantum Protocol

The existing protocol is connected to its experiment, explicitly listed
classical/quantum models, and Artifact. Lineage does not rerun comparison logic
or make superiority claims.

### Artifact Registry and reproducibility manifests

Artifact nodes preserve artifact ID, type, immutable status, and integrity hash.
Runs and models retain existing configuration/model hashes. Artifact contents
and storage paths are not copied into lineage.

## Frontend behavior

Experiment Detail contains a native **Lineage / Provenance** panel with:

- bounded depth and direction controls
- evidence and artifact filters
- layered, horizontally scrollable provenance nodes
- relationship and capture-state inspection
- node identity, status, version, timestamp, and fingerprint details
- partial, unresolved, and integrity-review states
- a machine-readable graph/integrity disclosure

Large graphs initially show 60 nodes and can be explicitly expanded. The panel
loads from the dedicated lineage endpoint and does not slow the base Experiment
Detail request.

## Privacy and security

Lineage contains identifiers, versions, hashes, fingerprints, statuses, and
safe relationship metadata. It never includes:

- raw CSV or biomedical rows
- patient or direct identifiers
- uploaded private record contents
- API tokens, passwords, credentials, or secrets
- hidden environment values
- internal filesystem paths

## Limitations

- Historical capture completeness depends on identifiers that were actually
  persisted by older versions.
- Shared-dataset use is provenance, not evidence that experiments are
  scientifically comparable.
- A complete lineage graph does not certify reproducibility, correctness,
  validity, or trustworthiness.
- The bounded relational implementation is intended for the current
  single-workstation research registry, not as a general-purpose graph store.