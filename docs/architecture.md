# Architecture

## Scope and design decisions

The supplied master prompt and mandatory biomedical specification are the source of requirements. This implementation is a local, single-user binary-classification research monorepo, not a clinical application. No additional generic specification was supplied. Where those two documents leave a choice open, the project uses the decisions below rather than claiming an unseen specification was implemented.

The frontend uses React/TypeScript with Vite, typed fetch services, route-specific forms, real API-backed charts and explicit empty states. The backend uses FastAPI routers, Pydantic request/response schemas, service modules, SQLAlchemy repositories and SQLite. There is no hosted inference service or hidden telemetry.

## Directory responsibilities

| Path | Responsibility |
|---|---|
| `backend/app/api` | HTTP routes, schema validation, optional token authorization, upload body limits |
| `backend/app/data` | CSV parsing, biomedical quality, immutable source provenance, reproducible splits |
| `backend/app/feature_engineering` | Deterministic ratios/logs, training-only imputation/scaling/selection/PCA |
| `backend/app/models` | Classical factory, shared training orchestration, schema-safe prediction |
| `backend/app/quantum` | Lazy Qiskit adapter, backend abstraction, circuits, VQC/QSVC |
| `backend/app/evaluation` | Positive-class metrics, fold summaries, calibration diagnostics |
| `backend/app/explainability` | Permutation/SHAP/perturbation explanations of frozen models |
| `backend/app/jobs` | Single-worker queue, state transitions, cancellation, failure retention |
| `backend/app/experiments` | Equivalent-condition comparison and HTML/JSON reporting |
| `backend/app/storage` | Registry entities, UUID paths, atomic artifact writes and integrity hashes |
| `frontend/src/pages` | Thirteen implemented workspace/detail screens |
| `scripts` | Database initialization, real runtime demo, static source inspection |

## Data flow

1. The multipart upload route validates metadata and bounds the whole request before CSV parsing. CSV bytes are stored under a generated UUID; their SHA-256 and aggregate quality are recorded.
2. Configuration validation establishes target, positive label, independent-sample assumption, feature list, optional deterministic subsampling, duplicate handling and shared partitions.
3. The worker receives an experiment/job identity. Each model receives fresh fold-local pipelines for CV and a final fit on the complete training partition.
4. Evaluation calculates separate training, validation and held-out results. Successful pipelines plus private partition indices are stored as local trusted artifacts. Failed models remain registry entries without invented metrics.
5. The frontend polls explicit job state. Comparisons join models only inside one experiment; reports include source/configuration, measured outputs and limitations.
6. Prediction validates the exact raw input schema and reloads a hash-checked trained pipeline. Sample input and prediction payloads are returned without persistence. Explicit explanation jobs persist aggregate influence only.

## Database relationships

`Dataset -> Experiment -> ModelRecord`; each `Experiment` has a `Job`; each `ModelRecord` may have multiple `ExplanationRecord` entries. `Experiment.parent_id` links a rerun to its original without overwriting either. Foreign keys are enabled. SQLite uses WAL and a busy timeout. A referenced dataset cannot be removed through the API.

Configuration and metrics are JSON columns. Raw records remain private CSV files, never ORM row-by-row medical-record objects. Model artifacts include raw-feature schema and private train/test indices to reconstruct frozen-model explanations. These private indices are not included in public experiment summaries.

## Worker state model

`queued -> running -> succeeded | partial | failed`. Cancellation changes an active job to `cancel_requested`, then `cancelled` at a checkpoint. Restart marks leftover active jobs `interrupted`; there is no fictional automatic resume. `partial` means at least one model completed and another failed. `progress` is stage-based completion, not elapsed-time forecasting or a model performance metric.

The executor has one worker and a bounded queue. A process-global quantum random seed is therefore not used concurrently by separate training jobs. This is not a distributed task system. Deploying multiple uvicorn processes would violate its ownership assumptions and is unsupported.

## Boundaries and alternatives

CSV-only upload, SQLite, lightweight executor, Vite, HTML/JSON export, four-qubit defaults and bounded explanations are explicit MVP choices. QNN or real quantum hardware is not a supplied mandatory concrete requirement; the implemented quantum estimators are VQC and QSVC. PDF export, authentication accounts, RBAC, external validation cohorts and model serving across independent workers are not silently simulated; their absence is documented in `limitations.md`.

No migration engine is bundled. Initial schema creation is idempotent, but future schema changes need explicit migrations/backups. Generated implementation is not proof of runtime compatibility.
