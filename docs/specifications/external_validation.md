# External Validation Engine Specification

## 1. Overview

The **External Validation Engine** evaluates an already-trained, explicitly **LOCKED** machine learning or quantum-classical hybrid model against an independent external dataset without retraining or refitting any component of the pipeline.

In biomedical machine learning, internal cross-validation or train/test splits often overestimate model generalizability due to site-specific protocols, institutional population characteristics, and unmeasured confounding. External validation assesses whether the fixed, frozen model maintains discriminatory and calibration performance when applied to an independent cohort.

```
TRAINING DATASET (DatasetVersion A)
          ↓
   Model Training
          ↓
  Trained ModelRecord + Locked Model Artifact (.dill)
          ↓
     [ LOCK MODEL ]
          ↓
EXTERNAL DATASET (DatasetVersion B - Distinct Hash)
          ↓
16-Step Preflight Schema Compatibility Inspection
          ↓
Reuse Frozen Preprocessing Pipeline (Zero Refit)
          ↓
External Predictions & Probability Generation
          ↓
Evaluation at Inherited Locked Threshold (No External Tuning)
          ↓
Internal vs External Delta & Generalization Gap Computation
          ↓
Persistent ExternalValidation Entity + Immutable Evidence Artifact
```

> **CRITICAL SCIENTIFIC & REGULATORY BOUNDARIES:**
> 1. **Zero Retraining / Zero Refitting**: The model weights, hyperparameters, decision threshold, scalers, imputers, and dimensionality reducers (PCA) remain completely immutable. Preprocessing transformers are applied via `transform()` only—never `fit()` or `fit_transform()`.
> 2. **Threshold Lock**: The external evaluation strictly inherits the model's locked threshold (`external_threshold_tuning: false`). Thresholds are never selected, tuned, or optimized against the external dataset.
> 3. **Non-Clinical Research Capability**: External validation evidence is for research evaluation only. It does not establish clinical safety, diagnostic efficacy, population-level generalizability, or quantum advantage.
> 4. **No Raw Biomedical Data Storage**: The validation record and generated evidence artifacts store strictly aggregate metrics, confusion matrices, schema diffs, and provenance hashes. No individual row records, PHI, or raw biomedical measurements are persisted.

---

## 2. Architecture & Data Model

### 2.1 Database Entity

The external validation engine persists records to SQLite via entity `ExternalValidation` (`external_validations` table) registered in migration `20261003_02_external_validation`:

| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR(36), PK | UUID identifier for the validation run |
| `model_id` | VARCHAR(36), FK -> `models.id` | Locked model being validated (indexed) |
| `external_dataset_id` | VARCHAR(36), FK -> `datasets.id` | External dataset evaluated against (indexed) |
| `external_dataset_version_id` | VARCHAR(36), FK -> `dataset_versions.id`, Nullable | Specific immutable dataset version snapshot |
| `operation_key` | VARCHAR(64), Nullable | Idempotency and deduplication key (indexed) |
| `status` | VARCHAR(32) | Validation lifecycle state: `completed` or `failed` |
| `threshold` | FLOAT | Inherited decision threshold locked from the model |
| `external_threshold_tuning` | BOOLEAN | Hardcoded `False`; verifies no threshold optimization occurred |
| `sample_count` | INTEGER | Number of external evaluation samples |
| `class_distribution` | JSON | External cohort ground-truth class distribution counts |
| `positive_class_ratio` | FLOAT | Proportion of positive samples in external cohort |
| `metrics` | JSON | Calculated external classification and calibration metrics |
| `internal_comparison` | JSON | Delta comparisons against internal held-out evaluation |
| `compatibility` | JSON | Feature match audit, dropped extras, and schema checks |
| `independence` | JSON | Cryptographic and metadata independence assessment |
| `provenance` | JSON | Complete execution provenance, software versions, and hashes |
| `warnings` | JSON | Non-blocking observations (e.g., extra features ignored) |
| `limitations` | JSON | 8 mandatory scientific, statistical, and clinical caveats |
| `sign_convention` | VARCHAR(64) | Explicit mathematical formula for deltas (`external - internal`) |
| `artifact_id` | VARCHAR(36), Nullable | FK to registered immutable evidence Artifact |
| `error_message` | TEXT, Nullable | Error diagnostic if validation failed preflight or inference |
| `execution_time_seconds` | FLOAT | Wall-clock execution duration in seconds |
| `created_at` | DATETIME | Timestamp of validation execution (indexed) |

### 2.2 Immutable Evidence Artifact

Upon successful validation, the engine registers an immutable artifact in the platform's artifact registry (`artifacts` table) with:
- `artifact_type`: `external_validation_evidence`
- `metadata`: Complete validation summary, metrics, comparison deltas, compatibility audit, independence declaration, and 8 mandatory limitations.
- File digest: SHA-256 integrity hash calculated over the canonical JSON payload.

---

## 3. Preflight Compatibility Engine (16-Step Verification)

Before any data transformation or inference begins, the engine runs a comprehensive 16-step preflight compatibility audit via `resolve_preflight()`:

1. **Model Resolution**: Verifies `model_id` exists in the model registry.
2. **Model Readiness**: Enforces model `status == "ready"`. Training or failed models are rejected (HTTP 409).
3. **Artifact Integrity**: Computes SHA-256 HMAC digest of the saved model bundle (`.dill`) and verifies it matches `ModelRecord.artifact_sha256` (HTTP 409 on corruption).
4. **External Dataset Resolution**: Verifies `external_dataset_id` exists.
5. **Dataset Version Resolution**: Resolves target `DatasetVersion` snapshot or active version.
6. **Dataset File Integrity**: Computes SHA-256 digest of stored external CSV and verifies match against recorded version hash.
7. **Dataset Distinctness**:
   - Rejects if `external_dataset_id == model.dataset_id` (HTTP 409).
   - Rejects if external version equals training version (HTTP 409).
   - Rejects if external CSV SHA-256 hash equals training CSV SHA-256 hash, even if uploaded under a different filename or dataset name (HTTP 409).
8. **Target Presence**: Verifies external dataset contains the required target column (HTTP 422).
9. **Target Leakage Prevention**: Enforces that the target column is strictly excluded from model feature inputs (HTTP 422).
10. **Binary Classification Invariant**: Asserts that external dataset target contains exactly 2 observed classes (HTTP 422 on ternary, multiclass, or single-class cohorts).
11. **Positive Label Resolution**: Verifies positive label is present in observed external classes, applying explicit user `label_mapping` if configured (HTTP 422 on mismatch).
12. **Feature Schema Match**: Compares external dataset columns with model required input features.
13. **Missing Feature Detection**: Blocks validation if any model input feature is missing from external dataset (HTTP 422).
14. **Extra Feature Handling**: Extra columns present in the external dataset are safely filtered out and recorded as non-blocking warnings (`compatible: true`).
15. **Type Compatibility**: Checks numeric vs. categorical types against model training expectations (HTTP 422 on incompatible type casting).
16. **Class Imbalance Warnings**: Flags cohorts with minority class samples $< 10$ to warn against severe metric variance.

---

## 4. Evaluation Methodology & Metric Sign Conventions

### 4.1 Frozen Pipeline Transformation

The external evaluation dataset $X_{\text{ext}}$ is transformed using the model bundle's frozen preprocessing steps:
- Imputer: Replaces missing values using statistics fitted solely on training data.
- Scaler: Standardizes features using training mean $\mu_{\text{train}}$ and variance $\sigma^2_{\text{train}}$.
- Selector / PCA: Projects onto principal components computed from training features.
- Model Inference: Predicts probabilities $\hat{p}_{\text{ext}} = f_{\text{locked}}(X_{\text{ext}})$.
- Binary Decision: Predictions are assigned via $\hat{y}_{\text{ext}} = \mathbb{I}(\hat{p}_{\text{ext}} \ge \tau_{\text{locked}})$.

### 4.2 Sign Conventions & Generalization Gap

To avoid ambiguity across platforms and literature, metrics and deltas are reported with explicit mathematical definitions:

$$\Delta = \text{metric}_{\text{external}} - \text{metric}_{\text{internal}}$$

- **Positive Delta ($\Delta > 0$)**: Performance on external cohort is **higher** than internal held-out test score.
- **Negative Delta ($\Delta < 0$)**: Performance on external cohort is **lower** than internal held-out test score.

The **Generalization Gap** is defined as the performance degradation from internal cross-validation/testing to external validation:

$$\text{Generalization Gap} = \text{metric}_{\text{internal}} - \text{metric}_{\text{external}} = -\Delta$$

### 4.3 Evaluated Metrics

The engine computes 11 primary classification and calibration metrics:
- `accuracy`
- `balanced_accuracy`
- `sensitivity` (recall / true positive rate)
- `specificity` (true negative rate)
- `precision` (positive predictive value)
- `f1` (harmonic mean of precision and sensitivity)
- `roc_auc` (area under ROC curve, when both classes are observed)
- `pr_auc` (area under Precision-Recall curve)
- `brier_score` (mean squared error of predicted probabilities)
- `log_loss` (cross-entropy loss)
- `confusion_matrix`: `{"tp": int, "fp": int, "tn": int, "fn": int}`

When a metric is mathematically undefined (e.g., zero positive predictions causing precision division by zero), the engine returns `null` for the metric and provides an explicit explanation in `metric_explanations`.

---

## 5. Mandatory Limitations & Clinical Caveats

Every external validation result, API response, and evidence artifact permanently embeds the 8 platform limitations:

1. **Research Evaluation Only**: External validation evidence is for research evaluation only and does not establish clinical safety or efficacy.
2. **Threshold Lock Policy**: Decision thresholds are strictly locked from the training experiment; external threshold tuning was not performed.
3. **Distribution Shift**: Metric differences reflect both model generalization and differences between internal and external cohort distributions.
4. **Site & Protocol Differences**: External datasets may differ in clinical protocol, patient demographics, measurement instruments, or missingness patterns.
5. **No Quantum Advantage Claim**: Performance of quantum or hybrid models on external datasets does not imply quantum computational advantage.
6. **Sample Size Sensitivity**: Performance estimates and calibration curves on small external cohorts have wide confidence intervals.
7. **Label Equivalence Assumption**: Mapping between internal and external target classes assumes biological and clinical equivalence across cohorts.
8. **Static Evaluation**: External validation represents a static snapshot and does not substitute for prospective clinical validation or post-market monitoring.

---

## 6. API Reference

### 6.1 `POST /api/validation/external`
Executes external validation of a locked model against an external dataset.

**Request Body (`ExternalValidationRequest`):**
```json
{
  "model_id": "8a9269ff-5deb-4738-8f34-872c6e19b8e5",
  "external_dataset_id": "b3251a5d-e7a1-494c-9343-8c454344db45",
  "external_dataset_version_id": null,
  "label_mapping": null
}
```

**Optional Headers:**
- `Idempotency-Key`: Reusing the key with the same configuration returns the existing validation record.

**Response Status Codes:**
- `201 Created`: Validation successfully executed and persisted.
- `404 Not Found`: Model or external dataset does not exist.
- `409 Conflict`: Model not ready, artifact integrity corrupted, or dataset not distinct (same ID or content hash).
- `422 Unprocessable Entity`: Schema incompatible, non-binary target, missing required features, or type mismatch.

### 6.2 `POST /api/validation/external/preflight`
Performs non-mutating preflight compatibility checks and returns detailed schema comparison.

**Response Body (`ValidationPreflightOut`):**
```json
{
  "compatible": true,
  "reasons": [],
  "warnings": [],
  "model_id": "8a9269ff-5deb-4738-8f34-872c6e19b8e5",
  "external_dataset_id": "b3251a5d-e7a1-494c-9343-8c454344db45",
  "external_dataset_version_id": "c1a2b3c4-...",
  "feature_compatibility": {
    "expected_features": ["age", "blood_pressure", "cholesterol"],
    "present_features": ["age", "blood_pressure", "cholesterol"],
    "missing_features": [],
    "extra_features": ["patient_center_id"],
    "type_mismatches": []
  },
  "label_compatibility": {
    "internal_positive_label": "positive",
    "external_positive_label": "positive",
    "observed_external_classes": ["negative", "positive"],
    "mapping_applied": false
  },
  "threshold_lock": {
    "locked_threshold": 0.523,
    "tuning_allowed": false
  },
  "independence": {
    "content_hash_distinct": true,
    "dataset_identity_distinct": true,
    "version_distinct": true,
    "independence_status": "declared_external"
  }
}
```

### 6.3 `GET /api/validation/external`
Lists historical external validation records with optional filtering by `model_id` or `external_dataset_id`, supporting pagination (`limit`, `offset`).

### 6.4 `GET /api/validation/external/{id}`
Retrieves complete `ExternalValidationOut` record including metrics, comparisons, and audit details.

### 6.5 `GET /api/validation/external/{id}/metrics`
Returns focused metric summary:
```json
{
  "validation_id": "...",
  "model_id": "...",
  "sample_count": 250,
  "threshold": 0.523,
  "metrics": { ... },
  "comparison": [
    {
      "metric": "sensitivity",
      "internal_value": 0.884,
      "external_value": 0.852,
      "delta": -0.032,
      "generalization_gap": 0.032,
      "direction": "external_lower",
      "interpretation": "External sensitivity decreased by 0.032 compared to internal held-out test set."
    }
  ]
}
```

### 6.6 `GET /api/validation/external/{id}/provenance`
Returns cryptographic provenance chain, including software dependencies, dataset hashes, model artifact hashes, and execution metadata.

### 6.7 `GET /api/models/{id}/external-validation`
Returns all external validation studies performed on the specified model record.

---

## 7. Flagship Demonstration Walkthrough

### Scenario: Early Stage Diabetes Risk Prediction
1. **Model Training**: A `logistic_regression` model is trained on the primary Sylhet Diabetes Hospital dataset (`early-stage-diabetes`), achieving internal sensitivity 0.912 and specificity 0.895 at an OOF-optimized threshold $\tau = 0.540$. The model record is persisted and locked.
2. **External Cohort Ingestion**: An independent external cohort from an ambulatory clinic is registered as `early-stage-diabetes-ambulatory`.
3. **Preflight Inspection**: `POST /api/validation/external/preflight` verifies that all 16 clinical symptom features are present and compatible, and confirms distinct SHA-256 digests.
4. **Validation Execution**: `POST /api/validation/external` executes frozen inference at $\tau = 0.540$.
5. **Results**:
   - External Sensitivity: 0.885 ($\Delta = -0.027$, Generalization Gap = 0.027)
   - External Specificity: 0.871 ($\Delta = -0.024$, Generalization Gap = 0.024)
   - Brier Score: 0.118 (internal 0.098)
6. **Evidence Preservation**: An immutable artifact `external_validation_evidence` is committed with complete cryptographic provenance and the 8 mandatory research caveats.
