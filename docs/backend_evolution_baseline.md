# EntangleX Q-Health Backend Evolution Baseline

**Audit scope:** repository `Itzx-kush/EntangleX-Q-Health_final` at `9eea34f523ea1b6312c9d4802d10f6db075b0145` (`main`)  
**Audit date:** 2026-10-02  
**Program:** SIH Problem Statement 26139 — Hybrid Quantum Machine Learning Platform for Early Disease Detection  
**Change policy:** audit-only. This document adds no runtime behavior, API, schema, dependency, migration, scientific change, or frontend change.

## 0. Executive baseline

The backend is a coherent single-workstation research prototype, not a thin demo. It already implements immutable-by-convention dataset registration, aggregate quality controls, leakage-resistant training-only preprocessing, deterministic stratified holdout/CV, classical and simulator-based quantum/hybrid estimators, out-of-fold threshold selection, model persistence with integrity checks, prediction, bounded explanations, robustness evaluation, comparison, reports, and a cryptographically checked precomputed demonstration package.

The architecture is a FastAPI monolith with Pydantic contracts, SQLAlchemy over SQLite, filesystem artifacts, and a one-thread in-process training manager. Scientific orchestration lives in service modules rather than a separate generic service/repository layer. SQL rows are registries; large datasets and fitted estimators are files. The current `Experiment` is simultaneously a configured run, an execution parent, a model comparison group, and a report scope. That conflation is the main constraint for future evolution.

### Capability disposition

- **Research-ready within its declared envelope:** CSV validation, binary-target quality checks, leakage controls, reproducible split/CV, classical training, fixed/sensitivity-first thresholding, model registry, prediction schema enforcement, bounded robustness, reports, integrity-aware local storage, and verified-demo publication.
- **Implemented and strongly tested when optional dependencies are installed:** VQC, QSVC, QNN, Aer/noise simulation, PennyLane + PyTorch hybrid training/persistence, hybrid SHAP, and fair classical/hybrid evidence comparison.
- **Partial by design:** authentication is one workspace-wide bearer token; execution is one process/one worker; recovery marks active work interrupted rather than resuming it; reports are generated files but are not first-class artifact records; no migration framework exists; no explicit dataset/pipeline/run/artifact versions exist beyond hashes/config snapshots.
- **Absent:** real-QPU execution, clinical validation, multi-user authorization, distributed execution, external validation workflow, statistical multi-seed studies, immutable manifest entities, feature-lineage entities, calibration laboratory, distribution-shift registry, and formal research-workspace lifecycle.

The safe strategy is **additive normalization around existing scientific functions**. Preserve current endpoints, Pydantic field names/defaults, model identifiers, threshold semantics, split logic, fitted bundle shape, model details/metrics JSON, and verified-demo identities. Introduce new entities and APIs beside them, then adapt legacy responses through compatibility projections.

## 1. Current architecture

### 1.1 Actual component map

```text
Browser / API clients
  |
  | HTTP /api; optional bearer token; Origin check; body/host/CORS middleware
  v
FastAPI application (app/main.py)
  +-- health, summary, system status
  +-- domain routers (app/api/*.py)
  |     +-- Pydantic request/response contracts (app/api/schemas.py)
  |
  +-- dataset services (app/data/*)
  |     +-- CSV parser, target detection, quality, built-in catalog
  |     +-- deterministic sampling, holdout and training-only CV
  |
  +-- pipeline/model services
  |     +-- feature engineering and sklearn Pipeline
  |     +-- classical factory / calibration
  |     +-- Qiskit adapters / PennyLane-Torch adapter
  |     +-- threshold selection, metrics, prediction
  |
  +-- execution orchestration (app/jobs/manager.py)
  |     +-- bounded persistent queue state
  |     +-- ThreadPoolExecutor(max_workers=1)
  |
  +-- evidence services
  |     +-- explainability, robustness, comparison, reports
  |     +-- alignment, resource advisor, demo readiness
  |
  +-- SQLAlchemy registry (SQLite WAL)
  |     +-- datasets, experiments, models, jobs, explanations,
  |         robustness_records
  |
  +-- restricted local filesystem storage
        +-- data/datasets/<uuid>.csv
        +-- models/<uuid>.dill
        +-- experiments/<uuid>.json|.html
        +-- packaged verified demo artifacts/evidence
```

### 1.2 Layer responsibilities and evolution posture

| Layer | Current implementation and dependencies | Extend later | Do not rewrite |
|---|---|---|---|
| Application boundary | `app/main.py`; FastAPI lifespan initializes directories/SQLite, validates and installs verified demo, starts/stops training manager. Adds request IDs, no-store/security headers, sanitized errors. | Versioned routers, richer auth context, observability metadata. | Existing `/api` routes, error privacy, startup demo validation. |
| Contract/schema | `app/api/schemas.py`; strict Pydantic v2 (`extra=forbid`, finite JSON). Encodes bounded scientific compatibility rules. | New versioned schemas; compatibility projections. | Existing model IDs, defaults, validation constraints, serialized field names. |
| API | Thin synchronous FastAPI routers calling services/manager. `/api/health` is intentionally unauthenticated; all other `/api` routes share `authorize`. | Add new resource endpoints rather than changing legacy shapes. | Current routes and status codes used by frontend/tests. |
| Dataset/domain service | `data/service.py`, `catalog.py`, `target_detection.py`, `quality.py`; validates exact bytes, stores provenance/hash, registers built-ins/demo. | Dataset-version records and lineage pointing to existing immutable bytes. | Parsing/diabetes derivation, quality blockers, target semantics, hash scope. |
| Split/preflight | `data/splitting.py`; duplicate policy, common sampling budget, stratified holdout, training-only stratified CV, split fingerprint. | Explicit preflight result/manifest entity. | Split order, leakage checks, index semantics, seed behavior. |
| Feature pipeline | `feature_engineering/*`; sklearn pipeline: deterministic feature engineering → column transforms/imputation/encoding → selection → optional PCA → optional angle scaling. | Versioned pipeline definition/lineage around the builder. | Fit-on-training-only behavior, ordering, categorical redaction, PCA semantics. |
| Model/training | `models/factory.py`, `models/training.py`; fresh estimator per CV fold and final fit, OOF threshold lock, held-out evaluation, bundle/details/metrics. | Run orchestration, multi-seed coordinator, richer evidence entities. | Metric definitions, final bundle contract, OOF/holdout boundary, supported estimator IDs. |
| Quantum | `quantum/*`; replaceable simulator provider, logical circuits, sklearn-compatible Qiskit classifier, deterministic resource advisor. | Hardware provider interface and circuit/resource registry behind explicit capability gates. | Simulator semantics, no-hardware claims, fair shared representation rules. |
| Hybrid | `models/hybrid.py`; sklearn-compatible PennyLane `default.qubit` + Torch head; custom persistence reconstruction. | Additional backends only as explicit new capability/version. | Current AngleEmbedding/StronglyEntanglingLayers/head behavior and IDs. |
| Evaluation | `evaluation/*`; metrics, calibration wrapper, threshold curve/selection, frozen-artifact robustness. | Statistical studies, calibration/threshold labs, shift/external-validation evaluators. | Sensitivity/specificity and undefined-metric handling, threshold lock, frozen robustness behavior. |
| Evidence | `explainability/*`, `experiments/comparison.py`, `reports.py`; persisted explanation/robustness rows and generated reports. | First-class evidence/artifact registry and typed report packages. | Non-causal wording, held-out/background restrictions, neutral comparison claims. |
| Persistence | SQLAlchemy registry + SQLite WAL; `create_all`, no migration tool. Minimal repository helpers `require`/`recent`. | Alembic or equivalent explicit migrations; normalized additive tables. | Existing table/column meanings and UUID identities. |
| Artifact storage | `storage/files.py`; UUID allowlist paths, atomic writes, SHA-256/HMAC, restricted unpickler. | Artifact metadata entity, content-addressable references, lifecycle policy. | Verification-before-load and prohibition on uploaded model artifacts. |
| Readiness/alignment | `demo_readiness.py`, `alignment.py`; validates package manifest/evidence/models and publishes exact fixed IDs; capability truth depends on imports. | Versioned readiness packages and runtime verification records. | Existing flagship package integrity and identity contracts. |
| Configuration/security | `config.py`, `api/security.py`, middleware; local/production network boundaries and bounded resources. | Principal/role model, audit events, secret rotation. | Raw-input log prohibition and production CORS/host restrictions. |

## 2. Complete API contract inventory

### 2.1 Cross-cutting contract

- Prefix: `/api`.
- Authentication: `/api/health` is public. Every route registered on the shared API router requires `authorize`: allowed Origin plus optional exact `Authorization: Bearer <QHEALTH_API_TOKEN>` comparison. An empty configured token means no bearer authentication.
- Responses use strict Pydantic schemas where declared. Errors are sanitized as `{"error":{"code","message","request_id"}}`; validation errors expose locations/types, not submitted values.
- Mutating scientific endpoints are synchronous except training/rerun creation, which return `202` and enqueue one background job. Robustness and explanation execute synchronously.
- All endpoints below are current contracts and should be preserved unless explicitly marked otherwise. Frontend use is based on `frontend/src/lib/api.ts` and `frontend/src/types/qhealth.ts`.

### 2.2 Health, dashboard, alignment, and planning

| Method/route | Purpose; request → response | Dependencies and side effects | Consumer / compatibility |
|---|---|---|---|
| GET `/api/health` | Runtime status, version, mode, auth flag, quantum availability, disclaimer. | `availability()` only; no persistence; public. | Frontend `qh.health`; **LOCKED**. |
| GET `/api/summary` | Registry counts and five recent experiments. | Reads Dataset/Experiment/ModelRecord/Job. | Dashboard; **LOCKED**. |
| GET `/api/system/status` | DB/storage/quantum/model capability/job facts. | Reads jobs; checks directories and imports. | System page; **LOCKED**. |
| GET `/api/alignment` | Deterministic SIH capability/showcase/preset/architecture contract. | Built-in catalog and package import checks; no execution. | Flagship/demo UI; **LOCKED**. |
| GET `/api/quantum/capabilities` | Package presence and simulator-only boundary. | `find_spec`; no runtime execution. | Quantum UI; **LOCKED**. |
| GET `/api/quantum/resource-policy` | Bounded simulator planning policy. | Schema bounds/settings only. | Resource advisor; preserve v1 fields. |
| POST `/api/quantum/resource-advisor` | `ResourceAdvisorRequest` → resource profile, budget state, valid reduced recommendation, historical measurements. | Reads up to 100 ready model records; never starts training. | Quantum UI; **LOCKED**, additive fields safe. |

### 2.3 Datasets

| Method/route | Purpose; request → response | Dependencies and side effects | Consumer / compatibility |
|---|---|---|---|
| GET `/api/datasets` | Paginated recent `DatasetOut[]`; `limit 1..500`, `offset>=0`. | Registry read. | Dataset/history UI; **LOCKED**. |
| GET `/api/datasets/library` | Five manifest-backed built-in datasets plus readiness. | Catalog/readiness verification cache. | Dataset library/demo; **LOCKED**. |
| GET `/api/datasets/readiness` | Counts and readiness per built-in slug. | Verified-package status. | Demo/system UI; **LOCKED**. |
| POST `/api/datasets/library/{slug}` | Optional `{target,positive_label}` → registered `DatasetOut` (`201`). | Reads packaged CSV; validates; atomically stores bytes; inserts Dataset; idempotent by hash/name/target/label. | Library UI; **LOCKED**. |
| POST `/api/datasets/inspect` | Multipart CSV plus optional target/positive label → `DatasetInspectionOut`. | Bounded upload; parses/detects target; no persistence. | Upload workflow; **LOCKED**. |
| POST `/api/datasets/upload` | Multipart `metadata_json: DatasetUploadMetadata` + CSV → `DatasetOut` (`201`). | Validates deidentified assertion/CSV/quality; atomic file then DB insert. | Upload UI; **LOCKED**. |
| POST `/api/datasets/demo` | Registers sklearn WDBC benchmark → `DatasetOut` (`201`). | Generates deterministic CSV; stores once. | Legacy demo; preserve. |
| GET `/api/datasets/{uuid}/readiness` | Readiness for a registered dataset. | Dataset read + origin/slug resolution. | Potential frontend integration; preserve. |
| GET `/api/datasets/{uuid}` | `DatasetOut`. | Registry read. | Frontend; **LOCKED**. |
| GET `/api/datasets/{uuid}/provenance` | Raw provenance JSON. | Registry read. | Not currently wrapped by frontend; compatibility-safe additive evolution. |
| POST `/api/datasets/{uuid}/validate` | `{features?: string[]}` → current aggregate quality report. | Integrity-verifies stored CSV, reparses, recomputes quality. | Dataset UI; **LOCKED**. |
| DELETE `/api/datasets/{uuid}` | Deletes unreferenced dataset (`204`). | Integrity check, file-first deletion with compensating restore, DB delete; rejects referenced datasets. | API client available generically; preserve semantics. |

### 2.4 Pipeline and training jobs

| Method/route | Purpose; request → response | Dependencies and side effects | Consumer / compatibility |
|---|---|---|---|
| POST `/api/preprocessing/preview` | `TrainingConfig` → `PreviewOut`. | Loads verified dataset, prepares split, fits pipeline on training only; no persistence. | Studio; **LOCKED**. |
| POST `/api/feature-selection/preview` | Alias of same implementation/shape. | Same. | Studio; **LOCKED**. |
| POST `/api/pca/preview` | Alias of same implementation/shape. | Same. | Studio; **LOCKED**. |
| POST `/api/training/jobs` | `TrainingConfig` → `{job,experiment}` (`202`). | Synchronous preflight/dependency checks; inserts Experiment+Job; submits worker. Scientific side effect is eventual model fitting/evidence persistence. | Training UI; **LOCKED**. |
| GET `/api/training/jobs` | Paginated recent `JobOut[]`. | Registry read. | Training UI; **LOCKED**. |
| GET `/api/training/jobs/{uuid}` | `JobOut`. | Registry read. | Polling/integration; preserve. |
| POST `/api/training/jobs/{uuid}/cancel` | Requests cancellation → `JobOut`. | Mutates status/state; cancellation observed only at checkpoints. | Training UI; **LOCKED**. |

### 2.5 Models, prediction, explainability, and circuits

| Method/route | Purpose; request → response | Dependencies and side effects | Consumer / compatibility |
|---|---|---|---|
| GET `/api/models` | Paginated recent `ModelOut[]`. | Registry read. | Model UI; **LOCKED**. |
| GET `/api/models/{uuid}` | `ModelOut`. | Registry read. | Model UI; **LOCKED**. |
| GET `/api/models/{uuid}/input-schema` | Exact original feature names/types, labels, nullable flag, imputer. | Integrity-loads fitted bundle. | Prediction UI; **LOCKED**. |
| GET `/api/models/{uuid}/demo-sample` | Withheld feature sample for built-in/demo datasets only. | Loads dataset/model; never available for uploaded data. | Demo prediction; **LOCKED security boundary**. |
| POST `/api/models/{uuid}/predict` | `PredictionRequest` (1..32 exact-schema samples, risk thresholds, optional influence) → `PredictionOut`. | Integrity-loads model; no input/prediction persistence. Optional non-hybrid perturbation or hybrid local SHAP. | Prediction UI; **LOCKED**. |
| POST `/api/models/{uuid}/explain` | `ExplanationRequest` → persisted `ExplanationOut` (`201`). | Uses bounded held-out subset and training background; inserts ExplanationRecord. | Explainability UI; **LOCKED**. |
| GET `/api/models/{uuid}/explanations` | Newest-first `ExplanationOut[]`. | Registry read. | Explainability UI; **LOCKED**. |
| GET `/api/models/{uuid}/circuit` | Stored fitted circuit metadata → `CircuitOut`; quantum models only. | Model row read; no artifact load. | Quantum/model UI; **LOCKED**. |
| POST `/api/quantum/circuit` | `CircuitRequest` → logical parameterized `CircuitOut`; no execution. | Requires Qiskit packages; builds/decomposes logical circuit and backend metadata. | Quantum UI; **LOCKED**. |

### 2.6 Experiments, comparison, robustness, evidence, and reports

| Method/route | Purpose; request → response | Dependencies and side effects | Consumer / compatibility |
|---|---|---|---|
| GET `/api/experiments` | Paginated recent `ExperimentOut[]`. | Registry read. | Experiment/history UI; **LOCKED**. |
| GET `/api/experiments/{uuid}` | `{experiment,models,jobs}`. | Registry reads. | Experiment UI; **LOCKED**. |
| GET `/api/experiments/{uuid}/comparison` | Computed neutral pairwise evidence and controlled-benchmark status. | Reads experiment/models/robustness; no persistence. | Comparison UI; **LOCKED**. |
| GET `/api/experiments/{uuid}/verified-evidence` | Exact validated packaged demo evidence. | Revalidates configured packaged identity/cache; no computation. | Verified demo UI; **LOCKED**. |
| POST `/api/experiments/{uuid}/robustness` | `RobustnessRequest` → bounded result envelope. | Loads frozen models/dataset; evaluates max 24 conditions; inserts RobustnessRecord per condition. | Robustness lab; **LOCKED**. |
| GET `/api/experiments/{uuid}/robustness` | Newest-first `RobustnessRecordOut[]`. | Registry read. | Robustness UI; **LOCKED**. |
| POST `/api/experiments/{uuid}/rerun` | Reuses original `TrainingConfig`, sets `parent_id`, returns queued job/experiment (`202`). | Same preflight/enqueue behavior as new job. | Experiment UI; **LOCKED**. |
| GET `/api/experiments/{uuid}/report?format=html|json` | Download generated report. | Reads registries; verifies model artifacts; computes comparison. HTML is atomically written to `experiments/<uuid>.html`; JSON is response-only. | Report UI; **LOCKED**. |

## 3. Current data model and storage contracts

SQLAlchemy uses SQLite (`data/qhealth.sqlite3`) with foreign keys, WAL, 30-second busy timeout, and `check_same_thread=False`. Tables are created with `Base.metadata.create_all`; there is no migration/version table. ORM relationships are represented by foreign-key IDs and explicit queries, not `relationship()` objects. No cascade behavior is declared; foreign-key restrictions therefore protect referenced parents.

| Entity/table | Key fields and lifecycle | Relationships / consumers | Mutability and preservation contract |
|---|---|---|---|
| `Dataset` / `datasets` | PK UUID; `name`, sanitized `filename`, exact-byte `sha256`, JSON `provenance`, JSON `quality`, `created_at`. | Parent of Experiment/ModelRecord; all data, training, prediction-background, readiness APIs. CSV at `data/datasets/<id>.csv`. | Source bytes/provenance are treated as immutable. Delete only if no experiment, after hash verification. Preserve hash scope and provenance meanings. |
| `Experiment` / `experiments` | PK UUID; `dataset_id` FK/index; nullable self-FK `parent_id`; `status`; JSON `config`; JSON `summary`; `created_at`. Status: queued → running → succeeded/partial/failed/cancelled/interrupted. | Parent of Job and ModelRecord; scope for comparison/robustness/report/rerun. Optional JSON snapshot. | Mutable status/summary; config should remain immutable after creation. `parent_id` means rerun lineage, not a general DAG. |
| `ModelRecord` / `models` | PK UUID; `experiment_id` FK/index; `dataset_id` FK; `model_type`; `status`; nullable `artifact_sha256`; JSON `details`; JSON `metrics`; `created_at`. | Prediction, explanation, comparison, reports, resource history. Artifact at `models/<id>.dill`. | Insert-on-attempt. Ready records point to integrity-checked artifacts; failed records contain sanitized error/config and no artifact. Preserve model IDs/types and JSON evidence fields. |
| `Job` / `jobs` | PK UUID; `experiment_id` FK/index; `status`, integer `progress`, text `state`, JSON `errors`, timestamps. | Training APIs/system status; one job is created per current experiment. | Mutable execution projection. Active states are queued/running/cancel_requested. Startup converts active to interrupted. |
| `ExplanationRecord` / `explanations` | PK UUID; `model_id` FK/index; `method`; JSON `result`; `created_at`. | Explanation create/list and reports. | Append-only in current APIs; no case/input entity. Result contains aggregate/local evidence but prediction endpoint local SHAP is not persisted. |
| `RobustnessRecord` / `robustness_records` | PK UUID; `experiment_id` and `model_id` FKs/indexes; perturbation type/level, seed, JSON `result`, timestamp. | Robustness history, comparison, reports. | Append-only; each model/scenario is a row. No uniqueness/idempotency constraint. |

### 3.1 Non-table state

- Dataset CSV, model dill, experiment JSON snapshot, and HTML report files are outside SQL.
- Model `artifact_sha256` is normally an HMAC-SHA256 over the dill bytes using a local `.artifact_key`; packaged demo models retain validated package SHA-256 and are accepted by the loader for compatibility.
- The fitted bundle contract includes estimator, exact features/numeric features, dataset ID/hash, train/test indices, complete training config, labels, and locked threshold metadata.
- Packaged demo manifest/evidence/model files are source-controlled resources. Startup validates and hydrates fixed registry/file identities transactionally per dataset.

### 3.2 Relationship map

```text
Dataset 1 ── * Experiment 1 ── * Job
   |              |  \
   |              |   └── * RobustnessRecord * ── 1 ModelRecord
   |              └── * ModelRecord 1 ── * ExplanationRecord
   └────────────────── * ModelRecord

Experiment.parent_id ──> Experiment.id (rerun lineage)
Filesystem model artifact ──> ModelRecord.id + artifact_sha256
Filesystem CSV ──> Dataset.id + sha256
Report/snapshot file ──> Experiment.id (not a database entity)
```

### 3.3 Model strengths and normalization gaps

Strong: stable UUIDs, explicit dataset/model/experiment links, source/artifact integrity, full JSON snapshots, retained failed attempts, append-only evidence, and referenced-dataset deletion protection.

Gaps: no Run separate from Experiment; no artifact/report entity; no dataset-version or pipeline-version entity; no schema migration history; no explicit immutable manifest row; no case/prediction record; no feature lineage; no job attempt/lease/recovery record; no external-validation dataset relation; JSON fields carry important contracts without DB-level validation/indexing; report file lifecycle is implicit.

## 4. Current scientific workflow

1. **Ingest/inspect (synchronous, optional, not persisted):** multipart CSV is byte/row/column/schema bounded; UTF-8 comma CSV only. Target candidates and positive label are heuristically ranked but manual selection is required when uncertain.
2. **Register (synchronous, persisted):** target is normalized for the diabetes-readmission special case, aggregate quality is computed, exact source bytes are atomically stored, and Dataset provenance/quality/hash is inserted. Registration asserts deidentification; it does not independently prove it.
3. **Validate/preflight (synchronous, recomputed):** selected features are checked for identifiers, target proxies, infinities, conflicting duplicates, target inclusion, and schema issues. Training rejects blockers.
4. **Prepare common sample/splits (synchronous in enqueue and worker):** exact duplicates are rejected or dropped explicitly; residual duplicate feature vectors are rejected. Optional stratified sampling occurs before a stratified holdout. Stratified CV is over training only. All models in an experiment share indices, seed, feature list, and representation config.
5. **Preview (synchronous, not persisted):** the preprocessor is fitted on training rows only and returns redacted selected features, PCA evidence, stages, split hash, and warnings.
6. **Enqueue (asynchronous thereafter, persisted):** dependency checks precede creation. Experiment stores config, dataset provenance, split metadata, software versions, limitations, and comparison fingerprint. Job is submitted to the single worker.
7. **Cross-validation (worker):** every fold receives a fresh complete pipeline. Fold labels/scores/probabilities and timings are collected. Calibration, when selected, wraps the whole classical pipeline with internal CV.
8. **Threshold selection:** OOF scores select either the configured fixed threshold or the sensitivity-first feasible threshold. Ties maximize specificity, then sensitivity, F1, and threshold. If infeasible, evidence remains infeasible and final usability falls back to the fixed rule. No holdout value selects the threshold.
9. **Final fit/evaluation:** a fresh complete pipeline fits all training rows, then evaluates the untouched holdout. Training, CV summary, test, calibration diagnostics, timing, operating point, representation, software, limitations, and quantum metadata are recorded.
10. **Persist model:** fitted bundle is dill-serialized and atomically stored; its integrity reference and ModelRecord are inserted. Individual model failure yields a failed record while other requested models continue; experiment can be `partial`.
11. **Predict (synchronous, not persisted):** exact raw feature schema is enforced; model/artifact/dataset consistency is checked. Locked threshold produces class; probabilities produce research LOW/MEDIUM/HIGH categories using request thresholds. Inputs and outputs are explicitly not persisted.
12. **Explain (synchronous, optionally persisted):** prediction influence is ephemeral. The explain endpoint uses a deterministic bounded holdout subset and training-only background, then appends an ExplanationRecord.
13. **Robustness (synchronous, persisted):** frozen ready models share the same dataset/features/test indices. Deterministic bounded original-space perturbations are evaluated at the locked threshold; every condition is appended.
14. **Compare/report (synchronous computed view):** pairwise classical/quantum evidence validates comparability and returns neutral conclusions. Reports gather provenance, configuration, metrics, operating point, explanations, comparison, and robustness; HTML is stored, JSON is downloaded only.
15. **Rerun (asynchronous):** original config is revalidated and enqueued as a new Experiment with `parent_id`.

### Workflow attributes

| Step family | Async | Persisted | Reproducible/bounded | Optional/model-specific |
|---|---|---|---|---|
| Inspect/quality/preview | No | Inspection/preview no; registered quality yes | Upload, dimensions and preview bounded; deterministic | Inspection optional |
| Training | Yes, one worker | Experiment, Job, ModelRecord, bundle, snapshot | Seeds/splits/config stored; sample/CV/model bounds | Quantum dependencies; calibration classical-only |
| Threshold/evaluation | Within training | Metrics/details/bundle | OOF selection deterministic; holdout isolated | Strategy configurable |
| Prediction | No | No | 1..32 samples; exact schema | Probability/risk depends on estimator |
| Explanation | No | Explain endpoint yes; prediction influence no | 2..32 held-out cases; background max 20 for hybrid SHAP | Quantum perturbation only; hybrid SHAP only |
| Robustness | No | Yes | ≤64 cases, ≤24 conditions; seeded | Perturbation applicability depends on features |
| Comparison/report | No | Comparison no; HTML file yes | Derived from frozen records | Controlled benchmark label only when conditions match |

## 5. Quantum architecture audit

### 5.1 Qiskit family

- `QuantumClassifier` is a sklearn adapter for `vqc`, `qsvc`, and `qnn`.
- Shared feature representation is enforced by `TrainingConfig`: PCA components must equal qubits and angle scaling must be enabled. Quantum and classical comparison models use the same full preprocessor.
- Circuit construction uses `zz_feature_map` and, for VQC/QNN, `real_amplitudes`; repetitions and linear/full entanglement are bounded.
- **VQC:** Qiskit ML `VQC`, COBYLA/SPSA, seeded initial point and algorithm globals, sampler/pass manager, objective callback.
- **QSVC:** `FidelityQuantumKernel` + `ComputeUncompute` + `QSVC`; no probability output; decision margin threshold units.
- **QNN:** `SamplerQNN` over composed feature map/ansatz, parity interpretation into two classes, wrapped by `NeuralNetworkClassifier`; probability output is class probability from the parity-aggregated sampler result.

### 5.2 Execution backends

- `StatevectorBackend`: `QMLSampler(shots=None)`; exact local simulation; no noise.
- `AerBackend`: `SamplerV2`; finite configured shots; deterministic seed; one-thread backend. Optional illustrative depolarizing error switches to density-matrix simulation. It is not a characterized device model.
- Aer pass manager uses optimization level 1 and `rz/sx/x/cx` basis with seeded transpilation.
- `QuantumBackend` is already a replaceable primitive-provider interface, but only local simulation implementations exist.
- Availability is package-presence detection, not runtime execution proof (`runtime_verified=False`).

### 5.3 PennyLane + PyTorch hybrid

- `PennyLaneTorchClassifier` is a real trainable hybrid estimator, not the Qiskit estimator family.
- CPU `default.qubit`, analytic shots, Y AngleEmbedding, `StronglyEntanglingLayers`, Pauli-Z expectations per qubit, then configurable dense Torch layers and one logit.
- Uses seeded Python/NumPy/Torch, deterministic algorithms warning mode, one Torch thread, BCE-with-logits, Adam/SGD.
- Metadata includes framework versions, parameter counts, resource specs when available, optimizer/training config, changed quantum weights, and simulator-only limitation.
- Persistence removes runtime QNode/model, stores NumPy state dict, reconstructs the runtime and weights on load.

### 5.4 Four distinct concepts

1. **Quantum estimator:** Qiskit VQC/QSVC/QNN classifier adapters consume a classical reduced representation and produce labels/probabilities/margins.
2. **Hybrid method:** PennyLane circuit outputs expectation features into a trainable PyTorch head; optimization is joint through backpropagation.
3. **Quantum simulator execution:** exact statevector, finite-shot/noisy Aer, and PennyLane `default.qubit` are local simulations.
4. **Real quantum hardware:** absent. There are no credentials, provider sessions, QPU jobs, transpiled hardware evidence, queueing, calibration snapshots, or hardware result persistence.

### 5.5 Safe quantum extension points

Preserve `QuantumBackend` and estimator/model IDs. Add hardware as a new provider with explicit execution type, credential isolation, job/result entity, provider/backend/calibration snapshot, transpilation metadata, and opt-in APIs. Do not silently reinterpret `backend`, `shots`, depth, noise, or simulator metrics as hardware evidence. Circuit/resource registries can ingest existing `quantum_metadata_` and `CircuitOut` without changing training.

## 6. Explainability architecture audit

| Method/path | Current semantics | Restrictions/persistence | Reuse potential |
|---|---|---|---|
| Permutation importance | Decrease in ROC-AUC under raw-feature permutation; negative values retained. | Frozen estimator, deterministic held-out subset, requires two classes; persisted by explain endpoint. | Stability across seeds/splits by aggregating unchanged outputs. |
| Legacy SHAP | Permutation SHAP over complete numeric raw inputs, model output function returns positive probability or decision score. | Numeric-only, no missing values, ≤20 training background rows, bounded held-out cases; persisted. | Cross-model comparison after normalizing output units. |
| Hybrid SHAP | Bounded adapter encodes mixed raw inputs, reconstructs valid frames, explains final positive-class probability. Local contract includes prediction context/base value; global endpoint aggregates absolute/signed contributions. | Training-only background, max 20; max 32 explained; unseen categories rejected; hybrid requires SHAP; endpoint persists global result, prediction local result remains ephemeral. | Explanation stability, comparison, feature lineage linking to original feature names. |
| Perturbation/sensitivity | Numeric ±0.25 training SD; categorical alternate observed training category; magnitude and directional deltas. | Qiskit models are restricted to this method; categories are not disclosed; persisted through explain endpoint or ephemeral in prediction. | Counterfactual research foundation only after feasibility/manifold constraints are added. |

All paths state non-causal limitations. They explain frozen model behavior, not biology, diagnosis, or complete quantum internals. Background comes from the training partition; explained samples come from the held-out partition. PCA/selection internals are described separately, while returned explanation features map to original raw feature names because perturbation/SHAP calls the whole fitted pipeline.

Future explanation stability/comparison should reference immutable model/run/split and append new evidence records. Counterfactual work requires a new typed method with constraints and must not relabel current perturbation output as a counterfactual. Feature lineage can begin from existing pipeline configuration, raw features, selected-feature metadata, PCA loadings, and categorical redaction rules.

## 7. Reproducibility and provenance matrix

| Item | Status | Current location/evidence |
|---|---|---|
| Exact dataset bytes/hash/scope | **CURRENTLY STORED** | CSV file; Dataset `sha256`; provenance hash algorithm/scope. |
| Source/domain/version/license/target/labels/features | **CURRENTLY STORED** | Dataset provenance and catalog manifest. |
| Dataset version identity beyond one registration | **PARTIALLY STORED** | User/source version string and hash, but no version series/entity. |
| Sample pool, sampled indices, train/test indices/counts | **CURRENTLY STORED** | Experiment summary; model details/bundle; sample-pool/split hashes. |
| CV fold assignments | **PARTIALLY STORED** | Fold count and split hash include fold arrays, but explicit CV indices are not returned/stored separately. |
| Seeds | **CURRENTLY STORED** | Training config, split fingerprint, model/hybrid/robustness metadata. |
| Preprocessing/feature engineering config | **CURRENTLY STORED** | Experiment/model config; fitted description in model details. |
| Fitted imputer/scaler/encoder/selector state | **CURRENTLY STORED** | Fitted estimator artifact; not separately queryable. |
| Feature selection scores/selected features | **CURRENTLY STORED** | Model preprocessing details and previews. |
| PCA config/loadings/explained variance | **CURRENTLY STORED** | Model preprocessing/details and verified preprocessing evidence. |
| Pipeline semantic version | **NOT STORED** | No pipeline version entity/code commit field. |
| Model/classical/quantum/hybrid configuration | **CURRENTLY STORED** | Training config and model/quantum details. |
| Threshold curve, strategy, feasibility, locked value | **CURRENTLY STORED** | Model metrics/details and fitted bundle. |
| Calibration config/diagnostics | **CURRENTLY STORED** | Config and metrics; classical-only. |
| Software versions | **CURRENTLY STORED** | Experiment summary and model details; Python/platform + key packages. |
| Source commit/build identity | **NOT STORED** | Not in live experiment metadata. |
| Training/CV/inference timings | **CURRENTLY STORED** | Model metrics. |
| Dataset/artifact/split/comparison hashes | **CURRENTLY STORED** | Dataset, ModelRecord/bundle, summaries/details. |
| Artifact hash algorithm/key identity | **PARTIALLY STORED** | Value stored; normal live algorithm is implicit HMAC; key is local and unversioned. |
| Experiment parent/rerun relation | **CURRENTLY STORED** | `Experiment.parent_id`. No clone distinction. |
| Immutable experiment manifest | **NOT STORED** | JSON config/summary exists but remains mutable and is not a typed manifest. |
| Explanation method/request/background/sample count | **CURRENTLY STORED** | Explanation result. Exact explained indices are not stored. |
| Robustness method/seed/fingerprints/software | **CURRENTLY STORED** | Robustness result JSON. |
| Report generation time/content | **PARTIALLY STORED** | Time inside response/file; HTML file unregistered, JSON not stored. |
| Quantum circuit/backend/shots/noise/resources | **CURRENTLY STORED** | Model quantum metadata/circuit; unavailable measurements remain null. |
| Hardware provider/calibration/job provenance | **NOT STORED** | Hardware execution absent. |

## 8. Job and execution architecture

- Queue: in-memory `ThreadPoolExecutor(max_workers=1)` plus persistent Job/Experiment rows. The database is not itself a claim/lease queue.
- Admission: preflight prepares data and checks optional dependencies before insertion. A process lock bounds active jobs; default max is 3, configurable 1..10.
- States: queued, running, cancel_requested, succeeded, partial, failed, cancelled, interrupted. `partial` means some requested models persisted and some failed.
- Work unit: one Job iterates all requested model types serially. Each model performs CV, final fit, evaluation, and persistence.
- Cancellation: cooperative only at explicit checkpoints before folds/final stages/persistence. A currently executing fit cannot be forcibly interrupted; completed model records remain.
- Failure: individual model exceptions create sanitized failed ModelRecords and Job errors; unexpected outer failure marks job/experiment failed. No raw records/exception messages are logged.
- Recovery: startup marks any active job/experiment interrupted. Work is not resumed; rerun creates a new experiment. Shutdown requests cancellation then waits for executor completion.
- Persistence ordering: model file is written before ModelRecord insertion; a DB failure after file creation can leave an orphan. Experiment snapshot failure is nonfatal and recorded as a warning.
- Concurrency: one application process is assumed. Multiple web processes would each start a worker and use only process-local locks; current queue/cancellation guarantees do not extend across processes.
- Quantum limits: shared max sample cap, 2..8 qubits, bounded repetitions/iterations/shots; no QPU scheduling.

Safe evolution boundary: keep `train_model`, `prepare_data`, model factory, thresholds, and bundle persistence as deterministic execution primitives. Add a persistent Run/Attempt orchestration layer around them. Do not introduce distributed infrastructure until idempotency, leases, artifact publication, and recovery semantics are explicit and tested.

## 9. Security and data-safety audit

| Area | Current protection | Known limitation | Future hardening area |
|---|---|---|---|
| Authentication | Optional constant-time bearer token for all non-health APIs. | Empty token allows access; one shared secret, no identity/roles/expiry. | Principal-scoped tokens/OIDC, role and dataset ownership rules. |
| Authorization | Origin allowlist plus shared router dependency. | No row-level authorization; Origin is not identity. | Explicit policies per dataset/run/artifact. |
| Upload bounds | Whole-body middleware, streamed file limit, CSV size/row/column bounds, UTF-8 and schema checks. | Middleware buffers entire bounded body; declared max includes multipart overhead only via fixed allowance. | Streaming parser/quota accounting if larger uploads are ever allowed. |
| File/path safety | Area/suffix allowlists, UUID filenames, resolved-parent check, sanitized source filename, atomic writes. | Local directory permissions/backup policy are deployment concerns. | Harden storage ownership, encryption/retention, backup integrity. |
| Artifact integrity | CSV SHA-256; live model HMAC; verified demo manifest/evidence/model hashes; restricted unpickler. | Dill remains a high-risk format; key fallback can be ephemeral if write fails; no key rotation metadata. | Safer model format where feasible, managed key lifecycle, artifact registry/signatures. |
| Raw-data privacy | Aggregate dataset outputs; categorical values redacted in quality/pipeline metadata; uploaded demo-sample forbidden; no raw request/exception logging. | Uploaded bytes are stored unencrypted locally; uploader deidentification is an assertion. Prediction inputs may exist in process memory. | Data classification, encryption, retention/deletion policy, privacy review. |
| Error handling | Sanitized AppError/validation/HTTP/500 envelopes with request IDs. | Broad middleware catch can obscure debugging without secure operator traces. | Structured internal telemetry that excludes data values. |
| Logging | Fixed events, opaque IDs, exception types only, JSON formatter. | Third-party libraries/ASGI server may log outside this logger. | Deployment log configuration, redaction tests, sink access policy. |
| CORS/hosts | Explicit local defaults; production requires HTTPS origins and non-wildcard hosts; credentials disabled for wildcard. | Defaults are development-oriented. | Environment validation and deployment tests per host. |
| Request IDs/headers | UUID request ID, no-store, nosniff, no-referrer. | No trace propagation across future workers. | Persist safe correlation IDs in run/job events. |
| Public demo | Only packaged/built-in datasets may expose a withheld sample; package integrity is validated. | Built-in data licenses/redistribution remain governance obligations. | Manifest governance and review workflow. |
| Database | Foreign keys, WAL, rollback context. | SQLite file is not encrypted; no migration ledger; single-workstation assumptions. | Explicit migrations, backup/restore tests, access permissions. |

## 10. Automated test coverage map

The suite contains 190 collected outcomes in the audited environment: **155 passed, 35 skipped** (the skips are quantum tests guarded by `RUN_QUANTUM_TESTS=1`). The non-skipped suite includes real hybrid integration when dependencies are present. Full optional-runtime import/package validation and source-controlled demo artifacts passed after installing the repository requirement files.

| Capability | Coverage assessment | Principal tests |
|---|---|---|
| Dataset ingestion/library/target detection | Strong | `test_data_quality`, `test_dataset_library`, `test_target_detection` |
| Validation/leakage/duplicates | Strong | `test_data_quality`, `test_pipeline_and_leakage` |
| Preprocessing/feature selection/PCA | Strong | `test_pipeline_and_leakage`, dataset library workflows |
| Classical models/training/registry | Strong | `test_training_and_registry`, `test_metrics_and_prediction` |
| Thresholds/sensitivity/specificity | Strong | `test_thresholds_and_evidence`, `test_metrics_and_prediction` |
| VQC/QSVC/Aer | Strong but opt-in execution | `test_quantum_optional`, one bounded QSVC library test |
| QNN | Strong but opt-in execution | `test_qnn` including API/registry/report/comparison |
| PennyLane/Torch hybrid | Strong | `test_hybrid_model`, `test_hybrid_diabetes_e2e` |
| Prediction | Strong | metrics/prediction, training registry, hybrid E2E |
| Explainability/SHAP | Strong for current bounded paths | hybrid adapter/E2E; service contract checks |
| Robustness | Strong | `test_robustness`, comparison tests |
| Comparison/fair benchmark | Strong | `test_fair_controlled_benchmark`, threshold/evidence |
| Storage/security | Strong | `test_security_storage`, `test_security_and_api` |
| Reports | Moderate | registry HTTP flow, QNN flow, hybrid E2E; content is not exhaustively snapshot-tested |
| Demo readiness | Strong | `test_verified_demo_readiness` |
| Deployment configuration | Strong for declared files/settings | `test_deployment_configuration` |
| SIH alignment | Strong | `test_sih_alignment` |
| Job cancellation/restart/recovery | Partial | API/state tests exist; race/crash/process-boundary recovery is not deeply exercised |
| Migrations/backward DB upgrades | Missing | No migration system exists |
| Multi-process concurrency | Missing | Architecture declares single process |
| Auth roles/tenant isolation | Missing | Feature does not exist |
| External validation/multi-seed statistics/shift | Missing | Features do not exist |

Important regression gaps: orphan cleanup after file-write/DB failure, full cancellation timing, process crash during model publication, backup/restore, explicit old-database upgrade tests, report artifact lifecycle, explanation exact-index provenance, and running the optional quantum execution set in default CI.

## 11. Frontend dependency map (read-only)

The frontend centralizes backend calls in `frontend/src/lib/api.ts` and response contracts in `frontend/src/types/qhealth.ts`. It uses bearer-token injection, omits browser credentials, disables cache, and expects the `/api` base unless configured.

### Locked frontend contracts

- All routes listed in §2 except provenance, readiness-by-registered-ID, and direct Job GET are represented in the client or generic API helper.
- Model identifiers are a closed frontend union: `logistic_regression`, `svm`, `random_forest`, `vqc`, `qsvc`, `qnn`, `hybrid_pennylane_torch`.
- `TrainingConfig` field names, defaults/meaning, pipeline/quantum/hybrid nested shapes, and dimension compatibility are assumed throughout studio forms.
- Dataset provenance/quality fields, target-detection candidate shape, readiness fields, fixed flagship slug/experiment/model identities, and verified evidence package shape drive the verified-demo experience.
- Experiment fields `id`, `dataset_id`, `parent_id`, `status`, `config`, `summary`, `created_at`; Job status/progress/state/errors; Model details/metrics; and response nesting in experiment detail are directly consumed.
- Prediction depends on labels, probability status, decision rule, locked threshold/source, risk thresholds/categories, influence, hybrid local explanation, limitations, and disclaimer.
- Quantum UI depends on capabilities, exact Circuit fields, resource policy/advisor shape, and simulator/hardware booleans.
- Reports are downloaded by existing route/query/filename behavior.

### Safe to evolve with a compatibility layer

- Additive fields in JSON objects.
- New versioned endpoints/entities for Runs, Artifacts, manifests, studies, external validation, or hardware jobs.
- Internally normalized tables if legacy `ExperimentOut`, `ModelOut`, `Comparison`, and verified evidence are projected unchanged.
- New model IDs only after frontend union/fallback handling is added; do not repurpose current IDs.

### Requires future frontend integration

Experiment/Run distinction, artifact browser, version/lineage UI, multi-seed/statistical studies, threshold/calibration lab, external validation/shift views, disagreement analysis, quantum resource registry/noise scaling/hardware status, evidence-package lifecycle, and orchestration/cache controls.

## 12. Architectural extension matrix

| Future capability | Reuse | New module/entity/API | DB/migration impact | Frontend / compatibility / scientific risk |
|---|---|---|---|---|
| Experiment / Run separation | Experiment config/summary, Job, ModelRecord | `ExperimentDefinition`, `Run`, compatibility projector | Add tables/FKs; backfill each current Experiment as definition+run while preserving ID route | New run UI later; highest compatibility risk; never reinterpret old IDs without mapping. |
| Artifact registry | `safe_path`, atomic/hash verification, report/model files | Artifact entity/service and download metadata APIs | Add artifact table; backfill model/report/snapshot references | Artifact UI optional; preserve current file paths/load behavior initially. |
| Immutable manifests | config, split metadata, software/fingerprints | Manifest entity/canonicalizer | Add immutable JSON/hash linked to Run | No immediate UI; scientific risk if canonicalization omits existing fields. |
| Dataset versioning | Dataset hash/provenance/catalog | DatasetFamily/DatasetVersion or additive parent/version fields | New tables or nullable FKs; map current Dataset one-to-one | UI later; never mutate source bytes or target semantics in place. |
| Pipeline versioning | PipelineConfig, builder, fitted description | PipelineDefinition/Version | Store semantic/code version and hash | Compatibility layer returns current config; changing stage semantics requires new version. |
| Feature lineage | raw features, selector scores, PCA loadings | FeatureLineage evidence schema/service | New evidence/artifact rows | New inspection UI; preserve categorical redaction. |
| Experiment preflight | `prepare_data`, preview, dependency checks | Preflight service/result entity/API | Optional preflight table | Studio integration useful; do not duplicate/diverge validation logic. |
| Multi-seed execution | enqueue/train_model/split fingerprints | Study/RunSeed coordinator | Study/run tables, parent links | New study UI; prohibit post-hoc cherry-picking claims. |
| Statistical validation | metrics/paired common holdout | statistics service/evidence | Evidence rows/artifacts | New charts; preregister tests/corrections and retain raw per-run evidence. |
| Threshold/calibration lab | thresholds/calibration/OOF outputs | typed study service/API | Store curves/candidates as evidence | New lab UI; must not tune on current test set or change locked legacy threshold. |
| External validation | fitted bundle/prediction/quality | validation cohort link/result | Dataset-role and validation-result tables | New mapping UI; schema/target harmonization must be explicit/versioned. |
| Distribution shift | quality distributions, external datasets | shift evaluator/evidence | Evidence rows/artifacts | New view; avoid clinical generalization claims. |
| Advanced robustness | current perturbation engine | scenario registry/study | Study/scenario/result tables | Additive UI; preserve `controlled-perturbation-v1`. |
| Model disagreement | predictions/common indices | disagreement evaluator | Evidence/result table | UI required; output is model behavior, not truth. |
| Circuit/resource registry | quantum metadata/circuit/resource advisor | CircuitArtifact/ExecutionResource | Artifact/resource tables | New quantum view; simulator and hardware fields must remain distinct. |
| Noise/scaling studies | Aer/noise config, resource advisor | QuantumStudy coordinator | Study/run/evidence tables | New view; compare controlled conditions only. |
| Hardware abstraction | `QuantumBackend` | provider adapter, QuantumExecutionJob | Credentials outside DB; job/result/calibration tables | Significant UI/security work; never fallback silently between hardware/simulator. |
| Resource/experiment planning | resource policy/advisor, preflight | Plan entity/API | Optional plan table | UI later; heuristics are not runtime promises. |
| Evidence packages | reports, verified package validator | EvidencePackage/manifest/export | Package/artifact tables and signing/version fields | Download/review UI; preserve nonclinical/neutral language. |
| Research workspace lifecycle | all registries | workspace/project/archive policy | Scope/status FKs across entities | Major UI/auth migration; avoid deleting referenced evidence. |
| Orchestration/caching | manager/checkpoints/fingerprints | run executor, cache-key service | attempts/leases/cache/artifact links | UI job states may expand; cache only exact scientific identities. |

## 13. Seventeen-stage backend evolution dependency roadmap

```text
1 Baseline freeze
  -> 2 Migration foundation
  -> 3 Artifact registry
  -> 4 Dataset versions
  -> 5 Pipeline versions + feature lineage
  -> 6 Experiment definitions / Runs
  -> 7 Immutable manifests + preflight
  -> 8 Orchestration / recovery / exact caching
  -> 9 Multi-seed studies
  -> 10 Statistical validation
  -> 11 Threshold & calibration laboratory
  -> 12 External validation
  -> 13 Shift, robustness & disagreement
  -> 14 Quantum circuit/resource registry
  -> 15 Quantum noise/scaling & hardware abstraction
  -> 16 Evidence packages & workspace lifecycle
  -> 17 Integration hardening, compatibility freeze & release
```

| Stage | Objective and prerequisites | Reuse / likely additions | Migrations, APIs, tests, frontend | Primary regression risks |
|---|---|---|---|---|
| 1 | Freeze current contracts and scientific behavior. Prereq: none. | This audit, current tests. | Documentation only; no migration/API/UI. | Incomplete baseline. |
| 2 | Introduce explicit backward-aware migration mechanism and schema versioning. Prereq 1. | SQLAlchemy entities/init. Add migration tooling/process only with justification. | Baseline migration; upgrade/rollback/old-DB tests. No UI. | Startup/data loss; demo fixed IDs. |
| 3 | First-class artifact metadata while legacy loaders remain authoritative. Prereq 2. | `storage/files`, model/report/snapshot paths. Add Artifact. | Add artifact table/APIs; backfill tests; optional artifact list UI. | Hash/HMAC mismatch, orphaning, unsafe downloads. |
| 4 | Dataset family/version identity and immutable manifests. Prereq 2–3. | Dataset/provenance/hash/catalog. | DatasetVersion tables/APIs/migration; compatibility DatasetOut. UI later. | Changed target/hash/delete semantics. |
| 5 | Version pipeline definitions and record raw→engineered→selected→PCA lineage. Prereq 3–4. | PipelineConfig/build/description. | PipelineVersion/FeatureLineage; inspection APIs/tests; optional UI. | Leakage, category disclosure, changed PCA output. |
| 6 | Separate reusable Experiment definition from concrete Run/attempt while mapping legacy experiment IDs. Prereq 2–5. | Experiment, Job, ModelRecord, rerun. | ExperimentDefinition/Run/Attempt tables and versioned APIs; frontend compatibility adapter. | Highest ID/status/report break risk. |
| 7 | Canonical immutable run manifest and persisted preflight. Prereq 4–6. | `prepare_data`, dependency checks, fingerprints/software. | Manifest/Preflight tables/APIs; canonicalization tests; studio can consume later. | Manifest omission/divergence from execution. |
| 8 | Durable single-workstation orchestration, idempotent publication, recovery, and exact cache keys. Prereq 3,6,7. | manager/checkpoints/artifacts. | Attempts/leases/cache links; job event APIs; recovery/concurrency tests. UI status additions. | Duplicate execution, stale cache, cancellation semantics. |
| 9 | Multi-seed study coordinator over immutable runs. Prereq 6–8. | run executor, split seeds, metrics. | Study/StudyRun entities/APIs; bounded scheduling tests; study UI. | Cherry-picking, resource exhaustion. |
| 10 | Paired statistical evidence over controlled runs. Prereq 9. | metrics/comparison/fingerprints. | StatisticalEvidence entity/API; methodology and null-handling tests; charts later. | Invalid independence/multiple-comparison claims. |
| 11 | Threshold and calibration laboratory without holdout leakage. Prereq 6–10. | thresholds/calibration/OOF evidence. | ThresholdStudy/CalibrationStudy APIs/entities; leakage tests; lab UI. | Test-set tuning, silently changing production threshold. |
| 12 | External validation with explicit cohort/feature/label mapping. Prereq 4–7,11. | dataset versions, frozen model bundles, metrics. | ValidationPlan/Result; mapping API; migration/tests/UI. | Semantic mismatch, hidden preprocessing refit, clinical overclaim. |
| 13 | Versioned advanced robustness, shift, and disagreement studies. Prereq 9–12. | robustness v1, quality distributions, prediction/common samples. | Study/scenario/evidence entities/APIs; deterministic tests; analysis UI. | Off-manifold interpretation and incomparable cohorts. |
| 14 | Register logical/fitted circuits and measured simulator resources as artifacts. Prereq 3,6–8. | circuit metadata, resource advisor. | Circuit/Resource records/APIs; extraction tests; quantum UI integration. | Fabricated/null resources, confusing logical depth with hardware. |
| 15 | Controlled noise/scaling studies and explicit hardware-provider abstraction. Prereq 9–10,14. | `QuantumBackend`, Aer, advisor. | QuantumStudy and HardwareJob/Result; provider APIs; credential/security/skip tests; UI. | Credential exposure, nondeterminism, simulator/QPU claim confusion. |
| 16 | Signed/versioned evidence packages and research workspace/archive lifecycle. Prereq 3–15. | reports/demo manifest validator. | EvidencePackage/Workspace/Archive entities/APIs; export/import/integrity tests; UI. | Broken references, deletion, privacy leakage. |
| 17 | End-to-end migration, performance, security, documentation, compatibility freeze, and release gate. Prereq all. | Entire suite and legacy clients. | Full old→new migration fixtures, API contract snapshots, optional quantum CI, frontend integration. | Any scientific/API regression; ungrounded claims. |

## 14. ENTANGLEX BACKEND EVOLUTION HARD LOCKS

1. Do not rewrite working scientific pipelines without strong justification and equivalence evidence.
2. Preserve backward compatibility whenever practical; use versioned/additive APIs and compatibility projections.
3. Prefer additive architecture over destructive replacement.
4. Do not silently change scientific metric definitions, undefined-value handling, or class orientation.
5. Do not change dataset semantics, target derivations, labels, or source bytes without explicit versioning.
6. Do not claim quantum advantage without measured, controlled evidence.
7. Do not claim clinical validation, clinical effectiveness, regulatory status, or population generalization.
8. Do not introduce diagnoses, treatments, or medical recommendations.
9. Never expose raw biomedical inputs, category values that may identify people, predictions, or submitted values through logs/errors.
10. Do not break existing model IDs, experiment IDs, fixed verified-demo IDs, or artifact associations without a tested compatibility layer.
11. Do not modify frontend visual design during backend evolution.
12. Frontend changes are allowed only when technically required for backend integration and must preserve visual behavior unless separately authorized.
13. Add no arbitrary dependency; every dependency needs a documented capability, security, maintenance, and deployment rationale.
14. Add no unnecessary cloud/distributed infrastructure. Preserve the single-workstation mode until durable local semantics are proven.
15. Every future change requires regression tests, including backward API and old-database upgrade tests where applicable.
16. Database migrations must be explicit, ordered, reversible where feasible, and backward-aware; never rely on `create_all` for upgrades.
17. Existing verified functionality is presumed correct unless code/test evidence shows otherwise.
18. Preserve training-only fitting, disjoint holdout, common comparison sample/split/representation, and OOF-only threshold selection.
19. Never tune, calibrate, select features, select thresholds, or select models on the held-out test set.
20. Preserve exact sensitivity/specificity and positive-label semantics; never convert undefined measurements to zero.
21. Preserve fitted model bundle readability and restricted, integrity-checked load behavior through a documented migration window.
22. Never accept uploaded serialized model artifacts into the current loader.
23. Do not expose uploaded dataset rows through demo/sample APIs. Public samples remain limited to approved packaged benchmarks.
24. Simulator execution, illustrative noise, logical circuit resources, and real-QPU execution must remain explicitly distinct.
25. Hardware execution must be opt-in, never a silent backend fallback, and must persist provider/backend/calibration/job provenance.
26. Do not relabel perturbation sensitivity as causal explanation or counterfactual evidence.
27. Cache reuse is allowed only for an exact immutable scientific identity (dataset bytes, split, pipeline, model, threshold protocol, software/environment policy).
28. Cancellation/recovery changes must retain completed evidence and must not publish half-written models as ready.
29. Verified-demo manifest, evidence, model identities, and integrity checks remain frozen unless replaced by an explicitly versioned package.
30. Preserve categorical redaction in aggregate quality/pipeline metadata.
31. Do not delete referenced datasets, runs, models, or evidence; use explicit archive/tombstone semantics in future lifecycle work.
32. New statistical claims must disclose seeds, sample units, pairing, uncertainty, multiplicity handling, and limitations.

## 15. Gap matrix

| Capability | Status | Implementation | Test coverage | Scientific importance | Architectural maturity | Upgrade need / priority |
|---|---|---|---|---|---|---|
| Dataset parsing/registration/integrity | DONE / STRONG | `data/service.py`, `storage/files.py` | Strong | Critical | Mature local | Version identity; high |
| Target detection/manual override | DONE / STRONG | `data/target_detection.py` | Strong | High | Mature | Persist decision provenance more explicitly; medium |
| Quality/leakage controls | DONE / STRONG | `data/quality.py`, `splitting.py` | Strong | Critical | Mature | Version rules; high |
| Training-only preprocessing | DONE / STRONG | `feature_engineering/*` | Strong | Critical | Mature | Pipeline version/lineage; high |
| Feature selection/PCA | DONE / STRONG | pipeline/transformers | Strong | High | Mature | Typed lineage; high |
| Classical models | DONE / STRONG | factory/training | Strong | High | Mature | Hyperparameter study orchestration; medium |
| VQC/QSVC/QNN simulator | DONE / STRONG | `quantum/*` | Strong, opt-in runtime | High for project | Mature bounded adapter | Registry/studies; medium-high |
| PennyLane/Torch hybrid | DONE / STRONG | `models/hybrid.py` | Strong | High | Mature bounded adapter | Version/resources; medium |
| Real hardware | FUTURE / OPTIONAL | Provider abstraction only | None | Research optional | Missing | Stage 15; low until governance ready |
| Metrics/OOF thresholds | DONE / STRONG | evaluation | Strong | Critical | Mature | Lab as additive evidence; high |
| Calibration | PARTIAL | classical wrapper/diagnostics | Moderate | High | Bounded | Study entity/external calibration; medium-high |
| Model persistence/registry | DONE / STRONG | ModelRecord + dill/HMAC | Strong | Critical | Mature local, coupled | Artifact registry/safer format; high |
| Prediction | DONE / STRONG | `models/prediction.py` | Strong | Critical | Mature | Versioned serving contract only; medium |
| Explainability | DONE / STRONG | `explainability/*` | Strong | High | Mature bounded | Stability/comparison/lineage; medium |
| Robustness v1 | DONE / STRONG | `evaluation/robustness.py` | Strong | High | Mature bounded | Scenario/study registry; medium |
| Model comparison | DONE / STRONG | `experiments/comparison.py` | Strong | High | Mature derived view | Typed evidence; medium |
| Reports | PARTIAL | `experiments/reports.py` | Moderate | Medium-high | Functional, unregistered file | Artifact/evidence package; high |
| Experiment provenance | DONE / STRONG | Experiment summary/model details | Strong | Critical | Rich JSON, conflated entity | Definition/Run/manifest; highest |
| Job execution | FOUNDATION EXISTS | `jobs/manager.py` | Moderate | Operational high | Single-process prototype | Durable attempts/recovery; high |
| Dataset versioning | FOUNDATION EXISTS | hash/provenance | Indirect | Critical future | Missing entity | Stage 4; high |
| Pipeline versioning/lineage | FOUNDATION EXISTS | config/description | Indirect | Critical future | Missing entity | Stage 5; high |
| Artifact registry | FOUNDATION EXISTS | safe files/hashes | Strong primitives | Critical future | Missing entity | Stage 3; highest |
| Multi-seed/statistics | MISSING | Single seed only | None | High | Missing | Stages 9–10; high |
| External validation/shift | MISSING | Limitations only | None | Critical before broader claims | Missing | Stages 12–13; high |
| Immutable manifests | FOUNDATION EXISTS | snapshots/fingerprints | Indirect | Critical | Missing entity | Stage 7; high |
| Auth/authorization | PARTIAL | bearer/origin | Strong current boundary | Data safety critical | Local prototype | Identity/RBAC if multi-user; context-dependent |
| Migration system | MISSING | `create_all` only | None | Operational critical | Missing | Stage 2; highest |
| Verified instant demo | DONE / STRONG | `demo_readiness.py`, package | Strong | Demo critical | Mature/fail-closed | Versioned package lifecycle; medium |
| Resource advisor | DONE / STRONG | `resource_advisor.py` | Strong | Medium | Mature heuristic | Plans/resources registry; medium |
| Research workspace lifecycle | MISSING | flat registries | None | Medium future | Missing | Stage 16; medium |

## 16. Known limitations and technical constraints

- Binary classification and independent-sample assumptions only; no grouped, longitudinal, temporal, multiclass, survival, or federated design.
- Single machine, single process, one training thread; SQLite and process-local locks define the concurrency envelope.
- `create_all` initializes but does not migrate existing schemas.
- Experiments conflate definition, run, job scope, comparison group, and report scope.
- Important evidence is stored in flexible JSON rather than typed/versioned rows.
- Dill ties artifacts to Python/package/class compatibility despite integrity and restricted loading.
- Optional quantum execution tests are skipped unless explicitly enabled; package/import and non-execution paths still pass.
- Precomputed demo readiness depends on all required optional classes being importable when artifacts are validated.
- Cancellation is checkpoint-cooperative, not preemptive. Crash recovery is interruption + rerun, not resume.
- No explicit cleanup/registry for orphaned model/report/snapshot files.
- Prediction requests/results are deliberately not persisted, limiting longitudinal case audit by design.
- Explanation records do not store exact explained row indices, only bounded method/result metadata.
- Robustness uses synthetic original-space perturbations that may be off-manifold.
- Resource advisor categories are deterministic policy heuristics; historical timings are observed but not promises.
- Authentication is suitable only for a bounded trusted deployment, not multi-tenant biomedical data processing.
- Local stored biomedical CSV/model/database files are not application-encrypted.
- No real hardware support and no evidence of clinical validation or quantum advantage.

## 17. Verification performed

No functional source was changed to satisfy verification.

| Check | Result |
|---|---|
| `python scripts/check_source.py` | Passed: 83 Python files and 13 JSON files parsed; zero failures. This check explicitly does not execute runtime/tests. |
| Backend `python -m pytest -q` after installing all repository requirement files | Passed: **155 passed, 35 skipped, 5 warnings**. Skips are quantum tests guarded by `RUN_QUANTUM_TESTS=1`; no test failure remained. |
| Frontend `npm ci --silent && npm run build` | Passed TypeScript and Vite production build. Existing warnings: a module is both statically/dynamically imported and the main bundle exceeds Vite’s 500 kB advisory threshold. |
| Git diff scope | Documentation file only. |

Initial testing without optional quantum/hybrid requirement groups correctly produced dependency/readiness failures; after installing the repository-declared optional groups, the suite passed. This confirms optional dependency separation is a real runtime contract, not merely documentation.

## 18. Final recommendations for Prompt 2

Prompt 2 should be a **migration and compatibility foundation**, not dataset versioning or Experiment/Run redesign yet.

1. Freeze machine-readable snapshots of current OpenAPI paths/schemas, frontend TypeScript contracts, SQL table/column definitions, model IDs, fitted bundle keys, and verified-demo IDs/hashes.
2. Select and introduce one explicit migration mechanism with a baseline migration matching the current six tables exactly. Prove upgrade of a populated current database and unchanged startup/read behavior.
3. Add a schema-version/compatibility policy and old-database fixture tests. Do not modify current scientific tables/fields in this stage.
4. Specify artifact publication invariants (write, hash, DB commit, cleanup/recovery) in preparation for Stage 3, but do not yet replace `save_model`/`load_model`.
5. Keep every existing endpoint and frontend response unchanged. Add no new scientific behavior.
6. Run the complete current regression suite, source check, frontend build, verified-demo integrity tests, and an old-database migration test as release gates.

The first structural addition after migration safety should be the artifact registry because Dataset Version, Pipeline Version, Run, manifest, and evidence-package entities all need stable artifact identity and publication semantics.
