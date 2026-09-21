# Dataset provenance and demo attribution

## Public benchmark

The runtime demonstration uses the Breast Cancer Wisconsin Diagnostic dataset distributed by scikit-learn's `load_breast_cancer`. It originates from the UCI Machine Learning Repository. UCI describes 569 instances and 30 input features, with CC BY 4.0 licensing and attribution to Wolberg, Mangasarian, Street and Street (1993).

Official sources consulted:

- UCI dataset and license: https://archive.ics.uci.edu/dataset/17/breast%2Bcancer%2B%20wisconsin%2Bdiagnostic
- DOI: https://doi.org/10.24432/C5DW2B
- sklearn dataset loader: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html
- CC BY 4.0 terms: https://creativecommons.org/licenses/by/4.0/

These counts describe the public source, not an application measurement or a fabricated result file. The application reads the installed loader at runtime and calculates its actual registration counts and hash. No data rows, pretrained model or benchmark output is bundled in this generated archive.

## Transformations recorded

The demonstration reconstructs CSV bytes from the loader's numeric feature frame, excludes identifier fields, adds the string target `diagnosis`, and explicitly maps sklearn target 0 to `malignant` and 1 to `benign`. It records the installed sklearn version and an exact SHA-256 of these reconstructed stored CSV bytes. This hash identifies the application's copy, not the original upstream raw-file hash.

The positive class is `malignant`; the negative class is `benign`. Generic prediction output refers to an anonymous sample. Registration is idempotent for matching name/hash. User uploads cannot mark themselves as the public demo through metadata; only the internal demo registration path sets that flag.

## User-provided datasets

Provide accurate source, version, domain, target and positive label, and confirm de-identification and independent-sample suitability. The uploader is responsible for authorization, licensing and scientific validity. The application records metadata; it does not verify a license grant or fetch the source URL.

Each source record retains exact stored-byte hash, upload timestamp, class distribution, feature schema and source reference. Per-experiment metadata additionally records transformations, split/sample budget, software environment and model identity. Referenced datasets cannot be deleted through the ordinary dataset API because doing so would break provenance and frozen-model explanation reconstruction.
