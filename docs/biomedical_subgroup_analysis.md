# Biomedical Subgroup Analysis & Stratified Evaluation

## Mission & Purpose

The **Biomedical Subgroup Analysis** system enables researchers to evaluate model and experiment behavior across **explicitly defined biomedical cohorts** (e.g., Age bands, Gender, symptom flags, comorbidities) to determine whether aggregate performance metrics obscure significant performance disparities across populations.

It answers the core research question:
> **“How did the same model and evaluation protocol perform across the predefined subgroups represented in the dataset, and how much evidence supports each subgroup result?”**

---

## Scientific Principles & Non-Goals

1. **Stratified Evaluation, Not Retraining:**
   - Evaluates the **already trained, locked model** on slices of the **held-out evaluation population** (`data.test`).
   - No retraining or model fine-tuning per subgroup occurs.
2. **Explicit Cohort Definitions:**
   - Cohorts are derived from dataset columns and documented metadata (e.g., Age `<40`, `40–59`, `60+`, or categorical attributes).
   - Cohorts are never silently invented or fabricated.
3. **Descriptive Evidence vs. Value Judgments:**
   - The platform reports empirical performance differences, confidence intervals, and disparity ratios.
   - It **does not** generate subjective verdicts (such as "the model is fair/biased").
   - It **does not** perform causal inference or patient profiling.
4. **Strict Privacy Safeguards:**
   - Zero patient identifiers, row IDs, or raw biomedical records are exposed or exported.
   - Aggregate statistics, cell counts, and metric confidence intervals are reported.

---

## Key Methodological Safeguards

### 1. Small-Subgroup Protection (`minimum_n`)
When a defined cohort contains fewer evaluation samples than the configured threshold (`minimum_n`, default 20):
- Cohort status is marked as `TOO_SMALL`.
- Performance metrics are **`WITHHELD`** with an explicit reason (`Subgroup sample size (N=...) is below minimum reporting threshold (minimum_n=...).`).
- Numbers are never fabricated, and sample variance distortion is prevented.

### 2. Single-Class Target Distribution Handling
In biomedical slices, a cohort may contain only positive cases ($Y=1$) or only negative cases ($Y=0$):
- Rank metrics such as ROC-AUC and PR-AUC cannot be mathematically computed when only one class is observed.
- The status is marked as **`UNDEFINED`** with the explicit reason: `Subgroup contains a single observed target class.`
- Arbitrary numbers (such as `0.5`) are never invented.

### 3. Rigorous Confidence Intervals
- **Classification Proportions (Accuracy, Sensitivity/Recall, Specificity, Precision):**
  - Computed using the **Wilson Score Interval** with continuity correction support, which maintains coverage even for small sample sizes and extreme proportions.
- **ROC-AUC Confidence Intervals:**
  - Standard error and 95% confidence intervals are computed using the **Hanley & McNeil (1982)** method based on positive and negative sample counts.

### 4. Missing Value Handling Policies
- `exclude` (default): Evaluates all non-null observations in the subgroup column.
- `separate_unknown_group`: Creates an explicit "Unknown / Missing" cohort to audit missing data behavior.
- `error`: Halts execution if missing values are detected in the chosen subgroup field.

---

## Architecture & Storage Model

The database entity is persisted via SQLAlchemy in `SubgroupAnalysisStudy`:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String (PK) | Unique study identifier (`subgroup-<uuid>`) |
| `schema_version` | String | Schema contract version (`subgroup_analysis_v1`) |
| `experiment_id` | String (FK) | Source experiment identifier |
| `model_id` | String (FK) | Evaluated model identifier |
| `run_id` | String (FK, Nullable) | Associated execution run identifier |
| `dataset_id` | String (FK) | Source dataset identifier |
| `dataset_version_id` | String (FK, Nullable) | Immutable dataset version identifier |
| `status` | String | Study lifecycle status (`completed`, `failed`) |
| `operation_key` | String | Unique idempotency key (`subgroup:<fingerprint>`) |
| `definition_fingerprint` | String | Deterministic SHA-256 hash of configuration |
| `subgroup_field` | String | Dataset column evaluated (e.g. `age`, `gender`) |
| `configuration` | JSON | Rules, minimum N, missing policy, reference group |
| `overall_population` | JSON | Population accounting & metrics for entire test set |
| `subgroups_results` | JSON | Per-cohort results, CIs, population accounting |
| `comparisons` | JSON | Deltas and disparity ratios vs. overall/reference |
| `limitations` | JSON | Scientific boundaries and limitations |
| `provenance` | JSON | Model and dataset provenance metadata |
| `artifact_id` | String (Nullable) | Associated artifact record if registered |
| `created_at` | DateTime | Timestamp of study initiation |
| `completed_at` | DateTime | Timestamp of study completion |

---

## REST API Specification

### 1. Preflight Validation
- **Endpoint:** `POST /api/experiments/{id}/subgroup-analysis/preflight`
- **Request Body:**
  ```json
  {
    "subgroup_field": "age",
    "minimum_n": 20,
    "missing_value_policy": "exclude"
  }
  ```
- **Response:**
  ```json
  {
    "feasible": true,
    "subgroup_field": "age",
    "field_data_type": "int64",
    "unique_values_count": 50,
    "missing_values_count": 0,
    "suggested_rules": [
      { "id": "age_u40", "label": "Age < 40", "field": "age", "operator": "less_than", "value": 40 },
      { "id": "age_40_59", "label": "Age 40–59", "field": "age", "operator": "between", "lower": 40, "upper": 59 },
      { "id": "age_60p", "label": "Age 60+", "field": "age", "operator": "greater_than_or_equal", "value": 60 }
    ],
    "eligible_samples": 100,
    "blockers": [],
    "warnings": [],
    "limitations": [...],
    "configuration_fingerprint": "a9f8..."
  }
  ```

### 2. Execute Subgroup Analysis
- **Endpoint:** `POST /api/experiments/{id}/subgroup-analysis`
- **Request Body:** `SubgroupAnalysisRequest`
- **Response:** `SubgroupStudyOut` with `schema_version = "subgroup_analysis_v1"`

### 3. List Studies
- **Endpoint:** `GET /api/experiments/{id}/subgroup-analysis`
- **Response:** Array of `SubgroupStudyOut` records.

### 4. Get Study by ID
- **Endpoint:** `GET /api/experiments/{id}/subgroup-analysis/{study_id}`
- **Response:** Single `SubgroupStudyOut` record.

### 5. Export Study JSON
- **Endpoint:** `GET /api/experiments/{id}/subgroup-analysis/{study_id}/export`
- **Response:** Machine-readable JSON download with header `Content-Disposition: attachment; filename="qhealth-subgroup-...json"`.

---

## Subsystem Integrations

1. **Deep Experiment Lineage (Prompt 13):**
   - Registered as evidence entity type in `ALLOWED_RELATIONSHIPS` (`selected_by`).
   - Included in `lineage_snapshot` specs for comprehensive node traversal.
2. **Research Evidence Packages (Prompt 12):**
   - Loaded in `_load_evidence` and inventoried under `"subgroup_analysis"`.
   - Referenced in package preflight and manifest gap tracking.
3. **Model Cards (Prompt 11):**
   - Linked to model records via `model_id` and included in Model Card source manifests.
4. **Experiment Reports (Prompts 14–15):**
   - Included in structured `report_data()` export and dedicated HTML report section.

---

## Scientific Boundaries

> **Platform Boundary Notice:**
> Biomedical Subgroup Analysis reports empirical performance differences across cohorts represented in the held-out dataset. It does not establish clinical safety, diagnostic efficacy, algorithmic fairness, or causal relationships. Uncomputed or withheld measurements remain explicitly documented, never fabricated.
