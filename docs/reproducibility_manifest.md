# Immutable Run Reproducibility Manifest

## Purpose

Every new training Run locks one compact, machine-readable provenance manifest
before it enters the scientific execution queue. The manifest records the
validated conditions that answer “what exactly produced this result?” without
copying raw biomedical rows, model binaries, report bodies, secrets, or
unrestricted environment variables.

The manifest extends the existing relationship:

```text
Dataset -> Experiment -> Run -> immutable experiment_manifest Artifact
                              -> Model / Evaluation / Quantum / Explanation / Report Artifacts
```

It does not introduce DatasetVersion, PipelineVersion, feature-lineage,
multi-seed, statistical, hardware, or evidence-package systems.

## Lifecycle and immutability

```text
Run created
  -> existing validation and deterministic split preparation
  -> server-resolved manifest assembled
  -> scientific configuration fingerprint calculated
  -> canonical manifest SHA-256 calculated
  -> immutable Artifact inserted and Run locked
  -> Run queued/running
  -> volatile Run/Job completion state and result Artifacts appended
```

The authoritative Artifact has type `experiment_manifest`, a unique operation
key per Run, no public storage URL, and `immutable=true`. There is no manifest
update API. Retrying creation returns the same Artifact; creating a manifest
after the Run leaves `created` is rejected. A changed scientific configuration
therefore requires a new Run.

Post-fit facts that do not exist before execution—fitted selected features,
PCA explained variance, an OOF-selected operating threshold, metrics and circuit
resources—are not guessed. The manifest identifies their integrity-registered
Model/Evaluation/Quantum Artifacts. Run lifecycle timestamps, elapsed time,
failure and cancellation remain volatile execution state and do not alter the
scientific configuration fingerprint.

## Schema

Schema version `1.0.0` is a strict Pydantic contract with these sections:

- identity and parent Experiment information;
- current Dataset identity, safe schema, source and exact-byte SHA-256;
- bounded sampling, duplicate behavior and sample-pool fingerprint;
- train/test strategy, counts and index fingerprints;
- stratified fold-local CV configuration and fold fingerprint;
- preprocessing and categorical encoding;
- log/ratio feature engineering;
- feature selection configuration;
- PCA and angle-scaling configuration;
- resolved configuration for every requested classical, Qiskit or
  PennyLane/PyTorch model;
- threshold/calibration protocol and explicit OOF/holdout boundary;
- evaluation metrics/conventions;
- installed software versions;
- safe platform, architecture, CPU-count and worker/simulator facts;
- execution state at lock;
- structured reproducibility status and limitations.

No feature/sample values, category vocabularies, raw indices, usernames,
hostnames, process IDs, tokens, headers or environment-variable values are
included.

## Canonicalization and hashes

`canonical_json_bytes` recursively normalizes JSON-safe values and serializes
UTF-8 JSON with sorted keys, no insignificant whitespace and stable separators.
Dictionary insertion order and display formatting therefore do not change a
hash.

- **Manifest hash:** SHA-256 of the complete canonical manifest with
  `identity.manifest_hash` represented as an empty string to avoid
  self-reference. It covers identity, timestamp, software/runtime context and
  every scientific section.
- **Scientific configuration fingerprint:** SHA-256 of Dataset, sampling,
  split, CV, preprocessing, feature engineering/selection, PCA, model/quantum,
  threshold and evaluation sections only. UUIDs, timestamps and runtime-machine
  facts are excluded.

The Artifact integrity hash and embedded manifest hash must match the
recomputed manifest hash. The Run stores only the Artifact reference,
configuration fingerprint, lock time and status for indexed lookup.

## Reproducibility status

New server-created manifests are
`CONFIGURATIONALLY_REPRODUCIBLE`: they contain the current Dataset hash, safe
schema, deterministic seeds and fingerprints, validated model/pipeline/
evaluation configuration, and software/runtime context. This is explicitly not
a claim of `BITWISE_REPRODUCIBLE`; floating-point libraries, optional quantum
frameworks and platforms can differ.

Legacy Runs without a manifest return `INCOMPLETE_PROVENANCE`. Missing evidence
is never reconstructed or invented. Existing Experiment, Run, Job, Model and
report APIs remain readable.

## Integrity and consistency verification

`verify_manifest_integrity(run_id)` checks:

- strict schema validity;
- Run, Experiment, Dataset and Artifact relationships;
- registered Dataset SHA-256;
- recomputed configuration fingerprint;
- recomputed canonical manifest hash;
- Artifact integrity hash and immutability;
- Qiskit/PennyLane metadata-family consistency.

Failure returns structured error codes and does not repair or overwrite the
Artifact.

## Protected APIs

All routes use the existing `/api` authorization and Origin policy.

| Route | Result |
|---|---|
| `GET /api/runs/{id}/manifest` | Artifact ID, strict manifest and current integrity result |
| `GET /api/runs/{id}/manifest/integrity` | Structured verification result |
| `GET /api/runs/{id}/provenance` | Compact Dataset → Run → Manifest → output Artifact graph |
| `GET /api/runs/{id}/reproducibility` | Status, fingerprint, manifest availability, integrity and limitations |

Example integrity result:

```json
{
  "valid": true,
  "run_id": "00000000-0000-0000-0000-000000000000",
  "artifact_id": "00000000-0000-0000-0000-000000000001",
  "manifest_hash": "sha256-hex-value",
  "configuration_fingerprint": "sha256-hex-value",
  "errors": []
}
```

The UUIDs and hashes above illustrate the response shape only.

## Migration and compatibility

Migration `20261002_02_immutable_run_manifest` additively adds nullable,
indexed Run fields for the manifest Artifact, configuration fingerprint,
reproducibility status and lock timestamp. Existing rows are not changed.
Fresh databases receive the same schema through SQLAlchemy metadata before the
idempotent migration is recorded.

Legacy limitations:

- pre-manifest Runs have no authoritative manifest Artifact;
- pre-Run Experiments/Jobs/Models still have no fabricated Run;
- post-fit metadata remains in the existing output Artifacts and model details;
- configurational reproducibility is bounded to current stored inputs and does
  not claim external or clinical reproducibility.