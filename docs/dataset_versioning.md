# Dataset Versioning and Dataset Cards

## Purpose

EntangleX now separates a logical **Dataset** from an immutable **Dataset Version**. A Dataset is the stable family/identity used by existing APIs. A Dataset Version is the exact, integrity-checked snapshot used by a scientific Run.

```text
Dataset (logical identity, backward-compatible current projection)
└── DatasetVersion v1, v2, ... (immutable snapshot)
    └── Run.dataset_version_id
        └── immutable Run manifest
            └── model, evaluation, explanation, report, and quantum artifacts
```

This addition does not change validation, splitting, preprocessing, training, thresholding, explainability, robustness, or quantum algorithms.

## Version lifecycle and immutability

Registration validates the CSV using the existing upload path, stores exact bytes in private application storage, computes SHA-256, computes a deterministic schema fingerprint, and creates the next `vN` record under the Dataset. Version numbers are sequential per Dataset and protected by database uniqueness constraints.

A version's bytes, target, positive/negative labels, schema identity, source identity, and content hash are immutable. There are no Dataset Version update or delete APIs. Changed data or target semantics creates another version.

Exact repeated scientific state is deduplicated by a version signature over:

- exact content SHA-256;
- schema fingerprint;
- target column;
- positive class; and
- negative class.

Submitting the same state returns the existing Dataset Version. The source metadata from a retry does not rewrite that immutable record.

## Integrity and schema identity

`content_sha256` covers the exact stored CSV bytes. `GET .../verify` recomputes the hash and reports mismatches without repairing or overwriting the file.

The schema fingerprint is SHA-256 over canonical JSON containing ordered columns, pandas dtypes, the target, positive class, and ordered feature structure. It contains no rows. It distinguishes schema/target-semantic changes from data-only changes.

## Dataset Cards

A Dataset Card is generated for one Dataset Version and contains compact sections for:

- identity and source reference;
- row/feature counts, feature-type counts, target, classes and class distribution;
- available quality summaries and validation status;
- content hash, schema fingerprint, origin and registration time;
- known warnings and missing-source limitations; and
- supported research use and public-demo restrictions.

Cards contain no sample rows, raw uploaded records, private filesystem paths, credentials, or clinical claims. A card documents a research snapshot; it is not evidence of clinical effectiveness or representativeness.

## Run and manifest integration

`TrainingConfig.dataset_version_id` is optional for backward compatibility. If omitted, training resolves the Dataset's current version. New Runs persist the resolved `dataset_version_id`; model bundles persist the same ID and content hash. Prediction, explanation backgrounds, and robustness evaluation resolve the exact version, preventing a later current-version change from changing historical model inputs.

The immutable Run manifest records:

- `dataset_id`;
- `dataset_version_id` and `dataset_version` label;
- exact Dataset Version SHA-256;
- exact Dataset Version schema fingerprint; and
- its private storage identity.

Legacy Runs and unverifiable historical Dataset rows retain `dataset_version_id = null`; provenance is not fabricated.

## Historical compatibility and migration

Migration `20261002_03_dataset_versioning` is additive and creates `dataset_versions`, `datasets.current_version_id`, `runs.dataset_version_id`, uniqueness constraints, and query indexes. It drops or rewrites no historical row.

At startup, historical Dataset rows are backfilled only when the original private CSV exists and its SHA-256 matches the recorded Dataset hash. Such a row receives a verifiable `v1`. Missing, malformed, or hash-mismatched historical data remains readable through the legacy representation and is not assigned invented version provenance.

The existing Dataset fields (`sha256`, `provenance`, `quality`, and filename) remain as the current-version compatibility projection, so existing endpoints and frontend consumers remain valid.

## Deletion safety

Dataset Version records have no destructive API. Dataset deletion remains available only for an entirely unreferenced Dataset. Any Experiment or Run reference blocks deletion. Before unreferenced files are removed, every stored version hash is verified; database failure restores files. This intentionally favors reproducibility over destructive cleanup.

## Version comparison

`GET /api/datasets/{dataset_id}/versions/compare?left=...&right=...` returns one of:

- `IDENTICAL_CONTENT` — identical stored bytes (target-semantic differences remain explicit in `differences`);
- `SAME_SCHEMA_DIFFERENT_DATA` — same schema fingerprint, different content; or
- `SCHEMA_CHANGED` — different schema/target fingerprint.

It reports only compact metadata differences. It is not distribution-shift or external-validation analysis.

## API reference

All routes use the existing bearer-token security dependency.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/datasets/{dataset_id}/versions` | List immutable versions |
| `POST` | `/api/datasets/{dataset_id}/versions` | Validate and register/reuse a version from multipart `metadata_json` and CSV |
| `GET` | `/api/datasets/{dataset_id}/versions/{version_id}` | Read version metadata |
| `GET` | `/api/datasets/{dataset_id}/versions/{version_id}/provenance` | Read safe version provenance |
| `GET` | `/api/datasets/{dataset_id}/versions/{version_id}/card` | Read the version-specific Dataset Card |
| `GET` | `/api/datasets/{dataset_id}/versions/{version_id}/verify` | Verify stored-byte integrity |
| `GET` | `/api/datasets/{dataset_id}/versions/compare` | Compare two versions by metadata/hash/schema |

Example training fragment:

```json
{
  "dataset_id": "<logical-dataset-uuid>",
  "dataset_version_id": "<immutable-version-uuid>",
  "models": ["logistic_regression"]
}
```

Omitting `dataset_version_id` preserves existing behavior by resolving the current version.

## Known limitations

- Version numbering is coordinated by the existing single-process application lock plus database constraints; this is not a distributed writer design.
- Dataset lifecycle archival is not introduced; referenced versions are retained and unreferenced Dataset deletion remains the only destructive operation.
- Dataset Cards reflect only metadata and quality evidence already generated by current validation; they do not infer population provenance.
- Comparison is content/schema metadata only. Distribution shift, external validation, pipeline versioning, and feature lineage remain out of scope.
- Existing logical Dataset APIs expose the current compatibility projection; version-aware clients should use the version routes for exact historical identity.
