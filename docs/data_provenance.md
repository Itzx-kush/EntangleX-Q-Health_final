# Dataset provenance and demo attribution

## Public benchmark

The runtime demonstration uses the Breast Cancer Wisconsin Diagnostic dataset distributed by scikit-learn's `load_breast_cancer`. It originates from the UCI Machine Learning Repository. UCI describes 569 instances and 30 input features, with CC BY 4.0 licensing and attribution to Wolberg, Mangasarian, Street and Street (1993).

Official sources consulted:

- UCI dataset and license: https://archive.ics.uci.edu/dataset/17/breast%2Bcancer%2B%20wisconsin%2Bdiagnostic
- DOI: https://doi.org/10.24432/C5DW2B
- sklearn dataset loader: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html
- CC BY 4.0 terms: https://creativecommons.org/licenses/by/4.0/

These counts describe the public source, not an application measurement or a fabricated result file. The legacy demo endpoint reads the installed loader at runtime and calculates its actual registration counts and hash. The Medical Dataset Library described below separately packages verified public CSV resources; no pretrained model or benchmark output is bundled.

## Transformations recorded

The demonstration reconstructs CSV bytes from the loader's numeric feature frame, excludes identifier fields, adds the string target `diagnosis`, and explicitly maps sklearn target 0 to `malignant` and 1 to `benign`. It records the installed sklearn version and an exact SHA-256 of these reconstructed stored CSV bytes. This hash identifies the application's copy, not the original upstream raw-file hash.

The positive class is `malignant`; the negative class is `benign`. Generic prediction output refers to an anonymous sample. Registration is idempotent for matching name/hash. User uploads cannot mark themselves as the public demo through metadata; only the internal demo registration path sets that flag.

## User-provided datasets

Provide accurate source, version, domain, target and positive label, and confirm de-identification and independent-sample suitability. The uploader is responsible for authorization, licensing and scientific validity. The application records metadata; it does not verify a license grant or fetch the source URL.

Each source record retains exact stored-byte hash, upload timestamp, class distribution, feature schema and source reference. Per-experiment metadata additionally records transformations, split/sample budget, software environment and model identity. Referenced datasets cannot be deleted through the ordinary dataset API because doing so would break provenance and frozen-model explanation reconstruction.

## Built-in Medical Dataset Library

Five small CC BY 4.0 datasets are packaged as backend application resources.
Runtime never downloads them. Every resource has a SHA-256 in
`backend/app/data/builtin_datasets/manifest.json`; selection verifies that hash
and registers the bytes through the same immutable dataset registry used by
uploads.

| Dataset | Authoritative source | Registered target |
| --- | --- | --- |
| Breast Cancer Wisconsin Diagnostic | UCI, DOI `10.24432/C5DW2B` | `diagnosis` |
| Early Stage Diabetes Risk Prediction | UCI, DOI `10.24432/C5VG8H` | `diabetes_status` |
| Heart Disease — Cleveland | UCI, DOI `10.24432/C52P4X` | `heart_disease` |
| Chronic Kidney Disease | UCI, DOI `10.24432/C5G020` | `ckd_status` |
| ILPD Liver Patient Dataset | UCI, DOI `10.24432/C5D02C` | `liver_disease` |

The exact attribution, license URL, packaged hash, class labels, normalization
steps, sample count and feature count are maintained in the manifest and copied
into registered provenance. Heart disease uses UCI's documented binary
interpretation (`num=0` absent, `num=1..4` present). Identifier columns are not
packaged. Missing feature values are preserved for the existing training-fitted
imputation pipeline. Source rows are not silently deduplicated; datasets with
exact duplicate rows disclose a recommended `drop_exact` experiment policy.

`POST /api/datasets/inspect` ranks upload target candidates using deterministic
name, cardinality, class-support, identifier, timestamp, missingness and
continuous-value signals. Its score is a heuristic ranking, not a calibrated
probability. Explicit target and positive-label values override the suggestion
and are revalidated during final registration.
