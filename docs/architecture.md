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
| `backend/app/runs` | Scientific Run creation, lifecycle transitions and Experiment lineage |
| `backend/app/artifacts` | Integrity-checked metadata registry for file-backed and metadata-only outputs |
| `backend/app/experiments` | Equivalent-condition comparison and HTML/JSON reporting |
| `backend/app/storage` | Registry entities, UUID paths, atomic artifact writes and integrity hashes |
| `frontend/src/pages` | Thirteen implemented workspace/detail screens |
| `scripts` | Database initialization, real runtime demo, static source inspection |

## Data flow

1. The multipart upload route validates metadata and bounds the whole request before CSV parsing. CSV bytes are stored under a generated UUID; their SHA-256 and aggregate quality are recorded.
2. Configuration validation establishes target, positive label, independent-sample assumption, feature list, optional deterministic subsampling, duplicate handling and shared partitions.
3. A training request creates an Experiment, one scientific Run, and one scheduling Job. The worker receives all three identities. Each model receives fresh fold-local pipelines for CV and a final fit on the complete training partition.
4. Evaluation calculates separate training, validation and held-out results. Successful pipelines plus private partition indices are stored as local trusted artifacts. Failed models remain registry entries without invented metrics.
5. The frontend polls explicit job state. Comparisons join models only inside one experiment; reports include source/configuration, measured outputs and limitations.
6. Prediction validates the exact raw input schema and reloads a hash-checked trained pipeline. Sample input and prediction payloads are returned without persistence. Explicit explanation jobs persist aggregate influence only.

## Experiment, Run, Job and Artifact

An **Experiment** is the durable research question/configuration scope. A **Run**
is one concrete scientific execution of that Experiment. A **Job** is the
infrastructure scheduling/progress record for a Run. An **Artifact** is an
integrity-registered output. Creating another execution through
`POST /api/experiments/{id}/runs` adds a Run and Job to the same Experiment
without duplicating the experiment definition.

Run states are `created -> queued -> running -> completed`, with terminal
`failed` and `cancelled` alternatives. Job states retain their historical
infrastructure vocabulary (`succeeded`, `partial`, `interrupted`, and so on).
A partially successful Job produces a completed Run whose result summary
truthfully records persisted and failed model counts; completion means the
scientific publication flow finished, not merely that a worker started.

Model files, evaluation results and quantum metadata are registered as immutable
Run artifacts. Explanations receive the producing model's Run lineage. The
existing HTML report is experiment-wide; it is linked to a Run only when the
Experiment has exactly one Run, and is registered as a mutable report artifact
because the legacy endpoint regenerates the same file. Artifact storage
references are internal relative paths, never public URLs.

Before a new Run moves from `created` to `queued`, the backend creates exactly
one immutable `experiment_manifest` Artifact. Its strict versioned content
captures current Dataset integrity, sample/split/CV fingerprints, resolved
pipeline/model/quantum/threshold/evaluation configuration, software versions
and safe runtime facts. The Run stores an indexed configuration fingerprint and
manifest reference. Volatile queue/start/completion/failure data remains on
Run/Job and does not change that fingerprint. See
`reproducibility_manifest.md`.

## Database relationships

`Dataset -> Experiment -> Run -> Job/ModelRecord/Artifact`; each `ModelRecord`
may have multiple `ExplanationRecord` entries. Existing direct
Experiment/Dataset links remain for compatibility. `Experiment.parent_id` still
links the legacy rerun endpoint to its original without overwriting either.
Foreign keys are enabled. SQLite uses WAL and a busy timeout. A referenced
dataset cannot be removed through the API.

Historical rows are not assigned fabricated Runs. Their nullable `run_id`
remains null and all legacy APIs continue to read them. New tables and nullable
foreign keys are installed by the additive, idempotent
`20261002_01_experiment_run_artifact` migration, recorded in
`schema_migrations`. No table or historical row is dropped or rewritten.

Configuration and metrics are JSON columns. Raw records remain private CSV files, never ORM row-by-row medical-record objects. Model artifacts include raw-feature schema and private train/test indices to reconstruct frozen-model explanations. These private indices are not included in public experiment summaries.

## Worker state model

`queued -> running -> succeeded | partial | failed`. Cancellation changes an active job to `cancel_requested`, then `cancelled` at a checkpoint. Restart marks leftover active jobs `interrupted`; there is no fictional automatic resume. `partial` means at least one model completed and another failed. `progress` is stage-based completion, not elapsed-time forecasting or a model performance metric.

The executor has one worker and a bounded queue. A process-global quantum random seed is therefore not used concurrently by separate training jobs. This is not a distributed task system. Deploying multiple uvicorn processes would violate its ownership assumptions and is unsupported.

## Boundaries and alternatives

CSV-only upload, SQLite, lightweight executor, Vite, HTML/JSON export, four-qubit defaults and bounded explanations are explicit MVP choices. QNN or real quantum hardware is not a supplied mandatory concrete requirement; the implemented quantum estimators are VQC and QSVC. Optional Supabase authentication adds identity and a private metadata-only activity stream without changing the research backend. PDF export, RBAC, external validation cohorts and model serving across independent workers are not silently simulated; their absence is documented in `limitations.md`.

The repository now has a deliberately small explicit SQLite migration runner
for additive local schema evolution. It is not a general distributed migration
engine; production changes still require backups, deterministic upgrade tests,
and one migration owner. Generated implementation is not proof of runtime
compatibility.
