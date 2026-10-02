# Distribution-Shift / Dataset-Shift Engine Specification

## 1. Overview & Research Objective

The **Distribution-Shift / Dataset-Shift Engine** is a first-class research diagnostic subsystem within EntangleX Q-Health designed to quantify observable statistical differences between a **Reference Dataset** (e.g., training cohort, historical baseline, or earlier version) and a **Comparison Dataset** (e.g., external clinical cohort, subsequent dataset version, or secondary demographic group).

```
REFERENCE DATASET (Baseline / Training)
              ↓
      Reference Profile
              ↓
COMPARISON DATASET (External / New Version)
              ↓
  DISTRIBUTION SHIFT ANALYSIS
              ↓
┌────────────────────────────────────────────────────────┐
│ 1. Schema Shift (shared, missing, extra, type check)  │
│ 2. Missingness Shift (delta = comp_rate - ref_rate)   │
│ 3. Target Prevalence Shift (class distribution delta) │
│ 4. Numeric Distribution Shift (KS-test, EMD, SMD)     │
│ 5. Categorical Distribution Shift (TVD, Chi-Square)   │
│ 6. Multiple Testing Correction (Benjamini-Hochberg)   │
│ 7. Model-Relevant Input Feature Filtering (Optional)  │
│ 8. External Validation Evidence Linkage (Optional)    │
└────────────────────────────────────────────────────────┘
              ↓
Structured Shift Analysis Record + Immutable Report Artifact
```

> **CRITICAL SCIENTIFIC & REGULATORY BOUNDARIES:**
> 1. **Research Diagnostic Only**: This subsystem evaluates statistical divergence across cohorts. It does not establish clinical safety, claim clinical harm, or assert clinical invalidity purely from statistical shift.
> 2. **No Automated Retraining**: The subsystem is purely diagnostic; it will NEVER trigger automated retraining, fine-tuning, or parameter adjustment.
> 3. **Non-Causal**: Statistical shift does not imply causal confounding, population representativeness, or individual patient risk.
> 4. **Direction Invariant**: All deltas and comparisons are strictly evaluated using the mathematical convention:
>    $$\Delta = \text{Comparison} - \text{Reference}$$
>    A positive delta indicates an increase in the comparison cohort relative to baseline; a negative delta indicates a decrease.
> 5. **Privacy & Data Protection**: No raw row records or protected health information (PHI) are persisted. Only summary statistics, histograms, test statistics, and cryptographic provenance digests are retained.

---

## 2. Architecture & Data Model

### 2.1 Database Entity

The engine persists all analyses in SQLite via entity `DistributionShiftAnalysis` (`distribution_shift_analyses` table), registered in migration `20261003_03_distribution_shift`:

| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR(36), PK | UUID identifier for the shift analysis run |
| `reference_dataset_id` | VARCHAR(36), FK -> `datasets.id` | Reference baseline dataset ID (indexed) |
| `reference_dataset_version_id` | VARCHAR(36), FK -> `dataset_versions.id`, Nullable | Immutable version snapshot of reference dataset |
| `reference_content_sha256` | VARCHAR(64) | Cryptographic SHA-256 hash of reference CSV content |
| `comparison_dataset_id` | VARCHAR(36), FK -> `datasets.id` | Comparison cohort dataset ID (indexed) |
| `comparison_dataset_version_id` | VARCHAR(36), FK -> `dataset_versions.id`, Nullable | Immutable version snapshot of comparison dataset |
| `comparison_content_sha256` | VARCHAR(64) | Cryptographic SHA-256 hash of comparison CSV content |
| `model_id` | VARCHAR(36), FK -> `models.id`, Nullable | Optional trained model whose feature set was analyzed (indexed) |
| `external_validation_id` | VARCHAR(36), FK -> `external_validations.id`, Nullable | Optional linked external validation run (indexed) |
| `parent_study_id` | VARCHAR(36), FK -> `multi_seed_studies.id`, Nullable | Optional linked multi-seed statistical study |
| `model_seed` | INTEGER, Nullable | Random seed inherited from the model if linked |
| `status` | VARCHAR(32) | Analysis lifecycle status: `completed` or `failed` |
| `operation_key` | VARCHAR(128), Nullable | Deterministic idempotency key for deduplication (indexed) |
| `policy_version` | VARCHAR(32) | Policy version string (`2026-10-03-v1`) |
| `configuration` | JSON | Configured thresholds, statistical tests, and correction method |
| `schema_analysis` | JSON | Column overlap, missing columns, extra columns, type mismatches |
| `target_analysis` | JSON | Class distributions, positive prevalence delta, and interpretation |
| `missingness_analysis` | JSON | Missingness rates and flagged missingness differences per feature |
| `feature_shifts` | JSON | Complete statistical test results, p-values, q-values, and effect sizes |
| `summary` | JSON | High-level counts of shifted features, tested hypotheses, and mismatches |
| `flagged_features` | JSON | List of feature names exceeding statistical or distance thresholds |
| `warnings` | JSON | Non-blocking observations (e.g., extra columns, sparse categories) |
| `limitations` | JSON | 11 mandatory scientific, clinical, and diagnostic caveats |
| `provenance` | JSON | Detailed environment provenance, software versions, and timestamps |
| `artifact_id` | VARCHAR(36), FK -> `artifacts.id`, Nullable | FK to immutable registered metadata artifact in artifact registry |
| `failure` | JSON, Nullable | Structured diagnostic record if analysis failed |
| `execution_time_seconds` | FLOAT | Wall-clock execution duration in seconds |
| `created_at` | DATETIME | Timestamp of analysis creation (indexed) |
| `completed_at` | DATETIME, Nullable | Timestamp of analysis completion |

### 2.2 Immutable Metadata Artifact

Upon completion of analysis, the engine registers an immutable research report in the platform's artifact registry (`artifacts` table) with:
- `artifact_type`: `distribution_shift_report`
- `operation_key`: `shift_artifact:{analysis.id}`
- `immutable`: `True`
- `metadata`: Full JSON report payload containing reference and comparison dataset hashes, policy version, configuration parameters, summary counts, individual feature shift tables, and limitations.

---

## 3. Preflight Compatibility Engine

The engine provides non-mutating preflight inspection via `resolve_shift_preflight()` (`POST /api/shift-analysis/preflight`):

1. **Reference Dataset Check**: Resolves `reference_dataset_id` from the dataset registry.
2. **Comparison Dataset Check**: Resolves `comparison_dataset_id` from the dataset registry.
3. **Version Resolution & File Integrity**: Resolves explicit or latest version snapshots, computes SHA-256 digests, and verifies match against recorded integrity hashes.
4. **Model Resolution (Optional)**: If `model_id` is supplied, validates that model exists, is `ready`, its HMAC-signed artifact (`.dill`) is uncorrupted, and extracts model input feature names.
5. **External Validation Resolution (Optional)**: If `external_validation_id` is supplied, verifies that the external validation entity exists.
6. **Same-Dataset Baseline Detection**: If reference and comparison datasets are identical, returns a non-blocking warning indicating zero-shift baseline behavior.
7. **Schema Preview**: Detects shared columns, columns missing in comparison, extra columns in comparison, and data type mismatches (e.g. numeric in reference, string in comparison).
8. **Target Distribution Preview**: If target columns match, extracts class counts and evaluates positive-class prevalence delta.
9. **Model Feature Audit**: If a model is provided, flags any required model features missing in the comparison cohort.

---

## 4. Statistical Methods & Computations

### 4.1 Direction Convention

All shift calculations adhere to:
$$\Delta = \text{Comparison} - \text{Reference}$$
- Missingness delta:
  $$\Delta_{\text{missing}} = \text{rate}_{\text{comparison}} - \text{rate}_{\text{reference}}$$
- Target prevalence delta:
  $$\Delta_{\text{prevalence}} = \text{prevalence}_{\text{comparison}} - \text{prevalence}_{\text{reference}}$$
- Mean difference:
  $$\Delta_{\mu} = \mu_{\text{comparison}} - \mu_{\text{reference}}$$

### 4.2 Missingness Shift

For each feature:
- Reference missing rate: $r_{\text{ref}} = \frac{n_{\text{missing, ref}}}{N_{\text{ref}}}$
- Comparison missing rate: $r_{\text{comp}} = \frac{n_{\text{missing, comp}}}{N_{\text{comp}}}$
- Absolute delta: $|\Delta_{\text{missing}}| = |r_{\text{comp}} - r_{\text{ref}}|$
- Flagged if $|\Delta_{\text{missing}}| \ge \text{missingness\_delta\_threshold}$ (default: `0.10`).

### 4.3 Numeric Distribution Shift

For every shared numeric column, the engine evaluates:
1. **Descriptive Statistics**: Count, mean, standard deviation, median, and interquartile range (IQR) for both cohorts.
2. **Two-Sample Kolmogorov-Smirnov Test**:
   $$D = \sup_x |F_{\text{comp}}(x) - F_{\text{ref}}(x)|$$
   Returns the empirical KS statistic $D \in [0, 1]$ and asymptotic two-sided p-value.
3. **Wasserstein-1 Distance (Earth Mover's Distance)**:
   $$l_1(u, v) = \int_{-\infty}^{\infty} |U(x) - V(x)| dx$$
   Quantifies the minimal work required to transform the comparison distribution into the reference distribution in original measurement units.
4. **Standardized Mean Difference (Cohen's $d$)**:
   $$\text{SMD} = \frac{\mu_{\text{comp}} - \mu_{\text{ref}}}{s_{\text{pooled}}}, \quad s_{\text{pooled}} = \sqrt{\frac{(n_{\text{ref}} - 1)s_{\text{ref}}^2 + (n_{\text{comp}} - 1)s_{\text{comp}}^2}{n_{\text{ref}} + n_{\text{comp}} - 2}}$$
   Interpreted using standard effect-size thresholds:
   - $|\text{SMD}| < 0.2$: `negligible`
   - $0.2 \le |\text{SMD}| < 0.5$: `small`
   - $0.5 \le |\text{SMD}| < 0.8$: `moderate`
   - $|\text{SMD}| \ge 0.8$: `large`

### 4.4 Categorical Distribution Shift

For every shared categorical column:
1. **Category Proportion Vectors**: Computes normalized frequencies across all observed categories in reference and comparison sets.
2. **Total Variation Distance (TVD)**:
   $$\text{TVD} = \frac{1}{2} \sum_{c \in \mathcal{C}} |p_{\text{comp}}(c) - p_{\text{ref}}(c)| \in [0, 1]$$
3. **Chi-Square Test of Independence**:
   Constructed from the $2 \times K$ contingency matrix of observed category counts.
   - **Sparse Category Cell Guard**: If any expected frequency in the contingency matrix is $< 5$, the test is flagged (`sparse_categories: true`) and a warning is attached noting that asymptotic Chi-square p-values may be unreliable.

### 4.5 Multiple Testing Correction: Benjamini-Hochberg (FDR)

When testing multiple features simultaneously, unadjusted p-values yield inflated family-wise false positive rates. The engine applies the Benjamini-Hochberg procedure across all $m$ evaluated feature hypotheses:

1. Rank all $m$ valid p-values in ascending order:
   $$p_{(1)} \le p_{(2)} \le \dots \le p_{(m)}$$
2. Compute adjusted p-values ($q$-values) enforcing monotonicity:
   $$q_{(m)} = p_{(m)}$$
   $$q_{(k)} = \min\left(1.0, \min\left(q_{(k+1)}, \frac{m}{k} \cdot p_{(k)}\right)\right) \quad \text{for } k = m-1, \dots, 1$$
3. Flagged hypotheses satisfy $q_{(k)} < \alpha$ (default $\alpha = 0.05$).

---

## 5. Feature Flagging Logic

A feature is flagged as having experienced significant distribution shift if any of the following deterministic criteria are met:
1. **Data Type Mismatch**: The column is numeric in one cohort and categorical/string in the other.
2. **Missingness Shift**: $|\Delta_{\text{missing}}| \ge \text{missingness\_delta\_threshold}$ (default: `0.10`).
3. **Numeric Shift**:
   - Adjusted p-value ($q$-value) $< 0.05$ **AND** either KS statistic $\ge 0.15$ or $|\text{SMD}| \ge 0.50$.
   - **OR** KS statistic $\ge 0.15$ regardless of sample size.
4. **Categorical Shift**:
   - Total Variation Distance $\ge 0.15$.
   - **OR** adjusted p-value ($q$-value) $< 0.05$ with non-sparse contingency cells.

---

## 6. Scientific Limitations (11 Mandatory Caveats)

Every shift analysis report automatically includes the following 11 explicit limitations:

1. **Statistical Association Only**: Distribution shift analysis quantifies statistical divergence between cohorts; it does not measure or establish clinical impact, patient harm, or diagnostic efficacy.
2. **Non-Causal Diagnostic**: Observed statistical shifts do not imply causal mechanisms, clinical confounding, or biological disease progression.
3. **No Retraining Implication**: The presence of statistical shift does not automatically imply that a predictive model is invalid or requires retraining, recalibration, or parameter tuning.
4. **Non-Clinical Research Capability**: This capability is strictly an engineering and research diagnostic for identifying dataset differences; it is not approved for clinical decision support or medical use.
5. **Sample Size Sensitivity**: Hypothesis tests (e.g., Kolmogorov-Smirnov and Chi-Square) are sensitive to sample sizes; very large cohorts may yield statistically significant p-values for clinically trivial differences, while small cohorts may lack power to detect meaningful shifts.
6. **Multiple Testing Correction**: False discovery rate adjustments (Benjamini-Hochberg) control the expected proportion of false positives across multiple features, but conservative or anti-conservative behavior can occur under complex feature dependencies.
7. **Sparse Category Cell Distortion**: Chi-Square tests of independence can produce unreliable or inflated p-values when expected cell counts fall below 5. Total Variation Distance should be consulted alongside test statistics.
8. **Unobserved Confounding**: Distribution comparisons evaluate only observed, recorded features; unmeasured clinical variables, institutional practices, and selection biases cannot be evaluated.
9. **Representation Caveat**: Neither cohort is assumed to be representative of the broader human or clinical population unless independently verified through epidemiological sampling.
10. **Target Shift Interpretation**: Changes in target class prevalence between cohorts reflect sample composition differences and should not be interpreted as changes in underlying disease incidence.
11. **Quantum Non-Advantage Statement**: Distribution-shift metrics apply equally to classical and quantum-assisted models; quantified dataset shift does not demonstrate or refute quantum advantage.

---

## 7. REST API Endpoints

### 7.1 Summary of Routes

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/shift-analysis` | Execute complete distribution shift analysis between two datasets |
| `POST` | `/api/shift-analysis/preflight` | Non-mutating preflight inspection and schema compatibility audit |
| `GET` | `/api/shift-analysis` | List recent shift analyses with optional dataset, model, or validation filter |
| `GET` | `/api/shift-analysis/{id}` | Retrieve complete shift analysis record and summary |
| `GET` | `/api/shift-analysis/{id}/features` | Retrieve detailed feature-by-feature shift analysis table |
| `GET` | `/api/shift-analysis/{id}/provenance` | Retrieve cryptographic provenance chain, file digests, and execution metadata |
| `GET` | `/api/datasets/{id}/shift-analysis` | Retrieve all shift analyses involving a specific dataset as reference or comparison |

### 7.2 Request Body (`POST /api/shift-analysis`)

```json
{
  "reference_dataset_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "comparison_dataset_id": "8bb38f21-7291-4e42-9fa4-7d526a718b52",
  "reference_dataset_version_id": null,
  "comparison_dataset_version_id": null,
  "model_id": null,
  "external_validation_id": null,
  "config": {
    "missingness_delta_threshold": 0.10,
    "numeric_distance_threshold": 0.15,
    "categorical_distance_threshold": 0.15,
    "statistical_significance_threshold": 0.05,
    "multiple_testing_correction": "benjamini_hochberg"
  }
}
```

---

## 8. Flagship Diabetes Demonstration Walkthrough

To verify distribution shift analysis on the verified Early Stage Diabetes dataset:

1. **Step 1: Upload Baseline Reference Cohort**:
   Upload the verified flagship `diabetes_data_upload.csv` as Dataset A.
2. **Step 2: Upload External Comparison Cohort**:
   Upload a second cohort representing an alternative clinical setting (e.g., shifted age demographic or altered polyuria prevalence) as Dataset B.
3. **Step 3: Run Preflight Audit**:
   Execute `POST /api/shift-analysis/preflight` with `reference_dataset_id` = Dataset A and `comparison_dataset_id` = Dataset B.
   - Verify `ready: true`.
   - Inspect `schema_preview.shared_columns` (16 clinical features) and `target_preview`.
4. **Step 4: Execute Shift Analysis**:
   Execute `POST /api/shift-analysis`.
   - Receive HTTP 201 with completed `DistributionShiftOut` record.
   - Verify `artifact_id` is registered.
   - Inspect `summary.shifted_features_count` and `flagged_features`.
5. **Step 5: Verify Audit Trail & Artifact**:
   Fetch `GET /api/shift-analysis/{id}/provenance` and `GET /api/artifacts/{artifact_id}` to verify cryptographic SHA-256 integrity hashes.
