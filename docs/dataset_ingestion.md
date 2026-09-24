# Dataset ingestion and compatibility

Q-Health is a tabular biomedical **binary-classification research** workflow. Dataset ingestion prepares an input for the existing quality, preprocessing, feature-selection, PCA, classical-model, and quantum-model stages; it does not change those algorithms.

## Curated local benchmarks

The Dataset Lab includes deterministic local snapshots of three public research benchmarks:

- **Breast Cancer Wisconsin Diagnostic** — UCI, 569 rows, 30 numeric features, `diagnosis` (`malignant` positive / `benign` negative).
- **Pima Indians Diabetes** — UCI, 768 rows, 8 numeric features, `outcome` (`1` positive / `0` negative).
- **Statlog Heart Disease** — UCI, 270 rows, 13 numeric features, `heart_disease` (`2` presence positive / `1` absence negative).

The source URL, version description, CC BY 4.0 attribution, target semantics, snapshot hash, and feature counts are returned by `/api/datasets/library`. Runtime does not fetch arbitrary URLs. These are benchmark inputs for demonstrations, not clinically validated datasets.

## Supported uploads

The Dataset Lab accepts UTF-8 **CSV**, **TSV**, **XLSX**, **XLS**, and **Parquet** files. Safe pandas readers normalize these into the existing internal dataframe workflow. Uploaded bytes remain unchanged in protected storage and are hashed with SHA-256. The original filename and format are stored in provenance.

Server-side controls remain active: the default maximum is 20 MB, 150,000 rows, and 200 columns. Configure these with `QHEALTH_UPLOAD_LIMIT_MB`, `QHEALTH_MAX_ROWS`, and `QHEALTH_MAX_COLUMNS`; do not treat them as unlimited ingestion settings.

## Inspector and compatibility

The flow is:

1. Select a built-in benchmark or choose an upload.
2. Inspect the file before registration.
3. Review row/column counts, numeric/categorical/boolean/datetime-like columns, missingness, infinity, duplicates, constants, low variance, high-cardinality categories, identifier-like columns, empty columns, and possible targets.
4. Explicitly choose the target and positive class.
5. Run compatibility analysis.
6. Register only after the target is valid and the compatibility findings are understood.
7. Continue through the existing Quality, Preprocessing, Features, PCA, and Training pages.

Compatibility is reported as `READY`, `WARNING`, or `BLOCKED` with individual checks. Missing targets, missing target values, one-class targets, multiclass targets, infinite numeric values, datetime-like columns, and unsupported complex values are blocked. Identifier-like fields, small samples, and high-cardinality categoricals are warnings for review. Q-Health never silently merges classes, fabricates labels, fetches remote files, or claims clinical validity.

Categorical and boolean scalar columns use the existing categorical encoding path. Datetime-like columns are not automatically converted into temporal features. Existing CSV clients can continue using `/api/datasets/upload`; `/api/datasets/inspect` and `/api/datasets/register` provide the explicit inspection-first flow.
