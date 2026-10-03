# Advanced Dataset Quality Scorecard & Data Readiness Assessment

## 1. Overview & Scientific Mission

The **Advanced Dataset Quality Scorecard** system in EntangleX Q-Health provides an explicit, structured, and reproducible assessment of dataset readiness, integrity, and compatibility for biomedical machine learning experiments.

The system addresses the fundamental scientific question:
> **"What is known about the quality, integrity, consistency, and research readiness of this exact dataset version for this exact experimental context?"**

### Core Architectural Principles
- **Readiness, Not Ranking**: Evaluates whether a dataset version satisfies experimental and clinical integrity requirements without asserting model-quality or performance superiority.
- **Strict Immutability & Non-Destructive Evaluation**: The scorecard observes and measures dataset characteristics. It **never cleans, mutates, or repairs data automatically**, preserving scientific truth.
- **Zero Raw Data Exposure**: All diagnostics compute aggregate statistics (cardinality, missing rates, bounds, variances). Raw patient rows or individual records are never stored in scorecard snapshots or emitted to logs.
- **Deterministic Fingerprinting**: Every scorecard produces a deterministic SHA-256 `assessment_fingerprint` over its canonical assessment dictionary, guaranteeing cryptographic reproducibility.
- **Idempotency**: Assessment runs support idempotent execution via `operation_key` deduplication.

---

## 2. The Nine Quality Domains

The assessment evaluates datasets across 9 comprehensive diagnostic domains:

| Domain | Scope & Description | Default Threshold / Blocker Criteria |
| :--- | :--- | :--- |
| **1. Schema Integrity** | Verifies column count, column names, expected target column presence, and data type regularity. | Fails if missing required columns or malformed schema. |
| **2. Completeness** | Measures missing and null value ratios across all features and target columns. | Fails if missing rate > 50% on key columns; warns if > 10%. |
| **3. Duplicate Integrity** | Detects exact row duplicates and feature-level duplicate rows. | Fails or warns based on duplicate policy (`reject` vs `drop_exact`). |
| **4. Target Integrity** | Verifies target presence, binary classification cardinality, missingness in target column. | Fails if target missing, has null values, or cardinality < 2. |
| **5. Feature Health** | Computes zero-variance (constant) features, low-variance features, and infinite values (`inf` / `-inf`). | Fails on infinite values; warns on constant / low-variance features. |
| **6. Class Balance** | Evaluates minority class representation and severe imbalance in target distributions. | Warns if minority fraction < 15%; fails if minority fraction < 5%. |
| **7. Data Leakage** | Identifies features with near-perfect correlation with target (potential target proxies or post-outcome measurements). | Warns/Fails if feature-target Pearson correlation > 0.98. |
| **8. Sensitive Fields** | Scans feature headers and distributions for direct patient identifiers (SSN, MRN, Name, Phone, Email, DOB). | Fails if direct identifiers are present in features. |
| **9. Context Compatibility** | Verifies compatibility against attached Experiment Protocols, Pipeline Versions, and Subgroup definitions. | Evaluates specific protocol constraints and pipeline feature sets. |

---

## 3. Composite Weighted Scoring & Status Classifications

Each domain produces a status (`PASS`, `PASS_WITH_WARNINGS`, `FAILED`, `BLOCKED`, `NOT_APPLICABLE`), passing check counts, and structured metric diagnostics.

A composite quality score (0.0 to 100.0) is derived from weighted domain contributions:
- **Completeness & Target Integrity**: 20% each
- **Schema & Feature Health**: 15% each
- **Class Balance & Leakage**: 10% each
- **Sensitive Fields & Duplicate Integrity**: 5% each

### Overall Statuses:
- **`PASS`**: All required and optional checks pass without warnings or failures.
- **`PASS_WITH_WARNINGS`**: All required checks pass, but non-blocking warnings exist.
- **`BLOCKED` / `FAILED`**: One or more critical integrity checks failed (e.g. direct identifiers, missing target, infinite values).
- **`INCOMPLETE`**: Required context or features were unavailable.

---

## 4. System Integrations

### Deep Experiment Lineage
- Registered as first-class `dataset_quality_scorecard` lineage nodes.
- Linked via `governed_by` and `derived_from` edges connecting datasets, dataset versions, and experiments.

### Scientific Audit Timeline
- Emits immutable events on execution:
  - `DATASET_QUALITY_ASSESSMENT_STARTED`
  - `DATASET_QUALITY_ASSESSMENT_COMPLETED`
- Records `operation_key`, `before_fingerprint`, `after_fingerprint`, and event SHA-256 checksums in the audit trail.

### Research Evidence Packages
- Scorecard metadata and diagnostic summaries are indexed as verified evidence artifacts (`artifact_type: dataset_quality_scorecard`) with immutable SHA-256 hashes.

### Cross-Scorecard Comparison
- Enables researchers to diff two scorecards (`compare_scorecards`), reporting:
  - Quality score delta ($\Delta$)
  - Check status transitions (e.g. `PASS` $\rightarrow$ `FAILED`)
  - Feature profile metric changes (variance, missing rates, bounds)

---

## 5. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/datasets/{id}/quality-scorecard/preflight` | Dry-run validation of parameters, schema, and threshold requirements without persistence. |
| `POST` | `/api/datasets/{id}/quality-scorecard` | Executes assessment, computes fingerprint, registers artifact and audit events, and persists scorecard. |
| `GET` | `/api/datasets/{id}/quality-scorecard` | Lists historical scorecards for a dataset (optional `version_id` query filter). |
| `GET` | `/api/datasets/{id}/quality-scorecard/latest` | Retrieves the most recent scorecard for a dataset or dataset version. |
| `GET` | `/api/datasets/{id}/quality-scorecard/{scorecard_id}` | Retrieves a specific scorecard by ID. |
| `GET` | `/api/datasets/{id}/quality-scorecard/compare` | Compares two scorecards (`base_id` and `target_id`) and returns structured diff. |
| `GET` | `/api/datasets/{id}/quality-scorecard/{scorecard_id}/export` | Exports machine-readable JSON or publication Markdown report. |
| `GET` | `/api/experiments/{id}/dataset-quality` | Resolves the governing scorecard for an experiment's dataset version. |

---

## 6. Clinical & Regulatory Boundary

> **IMPORTANT NOTICE:** The Dataset Quality Scorecard evaluates technical data readiness and computational integrity for biomedical machine learning research. It does **not** constitute clinical certification, regulatory device clearance (FDA / CE mark), diagnostic validity, or a medical guarantee of model safety.
