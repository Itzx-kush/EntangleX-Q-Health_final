# Multi-Seed Statistical Evaluation Engine Specification

## 1. Overview

The **Multi-Seed Statistical Evaluation Engine** provides rigorous, deterministic evaluation of machine learning and quantum-classical hybrid models across multiple random seeds in EntangleX Q-Health.

In biomedical and quantum machine learning research, single-seed evaluations can be misleading due to sensitivity to data partitioning, weight initialization, and stochastic optimization. This engine assesses **descriptive seed-to-seed stability** while preserving all reproducibility invariants of the EntangleX platform.

> **CRITICAL SCIENTIFIC CAVEAT:**
> Multi-seed evaluations quantify algorithmic variance and sensitivity to random seeds within a fixed sample split protocol. They **do not** establish clinical validity, clinical utility, population-level generalizability, or quantum advantage. All endpoints and artifacts explicitly embed these scientific limitations.

---

## 2. Architecture & Data Model

### 2.1 Database Entities

Two database entities are added to the SQLite storage layer (`backend/app/storage/entities.py`) via migration `20261003_01_multi_seed_evaluation`:

1. **`MultiSeedStudy` (`multi_seed_studies`)**:
   - `id` (VARCHAR(36), PK): UUID of the study.
   - `base_experiment_id` (VARCHAR(36), FK -> experiments.id): Base experiment providing dataset, preprocessing, and model configurations.
   - `status` (VARCHAR(32)): Study lifecycle state (`created`, `queued`, `running`, `completed`, `partially_completed`, `failed`, `cancelled`).
   - `seeds` (JSON): Ordered list of unique integer seeds (default: `[42, 123, 456, 789, 101112]`, bounded by `max_study_seeds=20`).
   - `config_override` (JSON, nullable): Immutable snapshot of locked base experiment configuration.
   - `summary_cache` (JSON, nullable): Cached descriptive statistics, bootstrap intervals, and paired comparisons.
   - `artifact_id` (VARCHAR(36), nullable): Foreign key to the immutable summary artifact registered in the artifact registry.
   - `error_message` (TEXT, nullable): High-level error if study execution fails before runs start.
   - `created_at`, `updated_at` (DATETIME).

2. **`StudyRun` (`study_runs`)**:
   - `id` (VARCHAR(36), PK): UUID of the association record.
   - `study_id` (VARCHAR(36), FK -> multi_seed_studies.id, indexed).
   - `seed` (INTEGER): Specific random seed for this run.
   - `run_id` (VARCHAR(36), FK -> runs.id, indexed): Standard durable scientific `Run`.
   - `status` (VARCHAR(32)): Seed execution state (`queued`, `running`, `completed`, `failed`, `cancelled`).
   - `error_message` (TEXT, nullable): Specific error if this individual seed run failed.
   - `created_at` (DATETIME).

### 2.2 Execution & Concurrency

- Execution runs on the single-worker background job manager (`backend/app/jobs/manager.py`) via `enqueue_study`.
- **Sequential Execution**: Runs are executed sequentially to avoid CPU/memory starvation and ensure reproducible timing.
- **Run Lifecycle**: Each seed run creates a durable `Run` entity transitioning cleanly through `created -> queued -> running -> completed/failed`.
- **Locked Manifests**: Every run generates an immutable, signed reproducibility manifest capturing exact package versions, hardware facts, dataset hash, and execution fingerprint.
- **Fault Isolation**: If a seed run fails (e.g., convergence failure or timeout), the error is isolated in `StudyRun.error_message`. Subsequent seeds continue execution. If at least one seed completes, the study enters `partially_completed` status.
- **Cooperative Cancellation**: `POST /api/studies/multi-seed/{id}/cancel` cooperative cancellation cancels queued seeds immediately without corrupting completed seed runs.

---

## 3. Statistical Methodology

### 3.1 Descriptive Aggregates

For each evaluated model and metric (e.g., `accuracy`, `roc_auc`, `f1`, `sensitivity`, `specificity`, `brier_score`), the engine computes:
- `mean`: Arithmetic mean across valid seed runs.
- `median`: Median value (50th percentile).
- `std`: Sample standard deviation ($s = \sqrt{\frac{1}{n-1} \sum (x_i - \bar{x})^2}$ for $n \ge 2$; `0.0` for $n=1$).
- `min`: Minimum observed value.
- `max`: Maximum observed value.
- `n`: Total seeds attempted.
- `valid_count`: Number of seeds yielding a valid numeric measurement.
- `missing_count`: Number of seeds with missing, NaN, or failed measurements.

### 3.2 Deterministic Bootstrap Percentile Intervals (95%)

To quantify stability without assuming normality:
- Number of bootstrap resamples: $B = 1000$.
- Resample generation: Deterministic pseudo-random resampling seeded by a SHA-256 digest of the input values and metric identifier.
- Percentiles: 2.5th percentile (lower bound) and 97.5th percentile (upper bound).
- For $n < 3$, bootstrap intervals are reported as `None` / `null` with an explanatory limitation note, preventing degenerate intervals from tiny samples.

### 3.3 Paired Seed Comparisons

When comparing two models (e.g., Classical Random Forest vs. Hybrid PennyLane + PyTorch):
- Only matched runs executed on the **exact same seed** are paired.
- Paired delta: $\Delta_i = \text{Metric}_{\text{target}, i} - \text{Metric}_{\text{baseline}, i}$.
- Descriptive statistics and deterministic bootstrap intervals are computed directly on the paired deltas $\Delta_i$.
- If seed sets do not match or have missing pairs, mismatched seeds are excluded from the paired delta calculation, and an explicit caveat is reported.

---

## 4. API Endpoints

Base path: `/api/studies/multi-seed`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/studies/multi-seed` | Create and enqueue a multi-seed study. Supports optional `Idempotency-Key` header. |
| `GET` | `/api/studies/multi-seed` | Paginated list of multi-seed studies (`limit`, `offset`). |
| `GET` | `/api/studies/multi-seed/{id}` | Detailed status of a study including progress and seed execution states. |
| `GET` | `/api/studies/multi-seed/{id}/runs` | List of all durable `Run` records associated with the study. |
| `GET` | `/api/studies/multi-seed/{id}/summary` | Aggregate statistics, 95% bootstrap intervals, and limitation statements. |
| `GET` | `/api/studies/multi-seed/{id}/comparison` | Paired cross-model delta statistics for matching seeds. |
| `POST` | `/api/studies/multi-seed/{id}/cancel` | Cooperatively cancel any pending/running seeds in the study. |

---

## 5. Artifact & Provenance Integration

Upon completion (or partial completion), the study engine registers an immutable summary artifact using the platform's artifact registry (`backend/app/storage/files.py` and `backend/app/artifacts/signer.py`):
- `artifact_type`: `study_summary`
- `content`: Canonical JSON of the complete statistical summary and paired comparisons.
- `sha256`: HMAC-SHA256 signature calculated with the platform artifact secret.
- Referenced by `MultiSeedStudy.artifact_id` for immutable provenance and auditability.
