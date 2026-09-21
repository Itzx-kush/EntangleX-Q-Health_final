# EntangleX Q-Health

**A research-oriented hybrid quantum-classical machine-learning platform for evaluating biomedical disease-risk prediction.**

> **Research Prototype:** This platform provides model-generated disease-risk predictions for research and decision-support purposes. Predictions are based on benchmark or user-provided datasets and are not a substitute for professional medical diagnosis, treatment, or clinical validation.

## Source-generation status

This repository contains generated application source, configuration, tests, and documentation. **The application, dependency installation, frontend/backend integration, Docker, automated tests, and quantum execution were not run or independently verified during generation.** Static source checks, when recorded in `docs/generation_status.json`, are not runtime tests. No model, benchmark result, performance screenshot, or fabricated prediction is bundled.

## 1. Overview and problem statement

Biomedical classification research needs traceable data, isolated evaluation, clear positive-class definitions, and comparisons that do not presume quantum superiority. EntangleX Q-Health implements that workflow as a local research prototype: validate data, configure a shared training pipeline, compare classical and quantum models, explain frozen predictions, and preserve experiment provenance.

The first demo uses the public **Breast Cancer Wisconsin Diagnostic** benchmark distributed with scikit-learn. The dataset is registered at runtime; no patient-identifiable information is added. This is a diagnostic-label classification benchmark, **not evidence of prospective early detection**. Other biomedical binary-classification datasets use the same metadata-driven architecture.

## 2. Architecture and technology stack

```text
React / TypeScript / Vite
          | same-origin /api
FastAPI routers + strict Pydantic schemas
          | services / repositories
SQLite experiment, model, dataset and job registries
          | single-process bounded training worker
Shared split -> fold-local sklearn Pipeline -> classical OR quantum estimator
          | trusted local artifacts + immutable dataset hashes
Measured evaluation / explanations / research predictions / HTML and JSON reports
```

The backend uses Python, FastAPI, Pydantic 2, SQLAlchemy 2, pandas, NumPy, scikit-learn, SHAP, Qiskit, Qiskit Machine Learning and Qiskit Aer. The frontend uses React 19, TypeScript 5.9 and Vite 7. There is no external analytics, hosted inference API, cloud account, or real-quantum-hardware requirement.

## 3. Prerequisites and version assumptions

Target **64-bit CPython 3.11**, **Node.js 22.12.0 in the 22.x line**, npm, and an ordinary desktop browser. Docker Compose v2 is optional. The direct dependency set and frontend lockfile were verified in a clean environment; Docker runtime and complete application execution remain separate checks. Full quantum dependencies are substantially heavier than the classical-only installation.

Backend direct dependencies are pinned to the verified environment documented in [verified environment](docs/verified_environment.md). Qiskit Machine Learning is **0.9.1**, Qiskit is **2.5.2**, and Aer is **0.17.2**. The committed `frontend/package-lock.json` is the authoritative npm lockfile; use `npm ci` for a clean, reproducible install. See [dependency assumptions](docs/dependency_assumptions.md).

## 4. Installation: Windows PowerShell

Extract `ENTANGLEX-Q-HEALTH.zip`, open a terminal in the extracted parent folder, and run:

```powershell
cd entanglex-q-health
py -3.11 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm ci
cd ..
```

Using the virtual environment's Python executable directly avoids PowerShell activation-policy changes. Installation runs on your workstation, not as part of source generation.

### Linux / macOS alternative

```bash
cd entanglex-q-health
python3.11 -m venv .venv
cp .env.example .env
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python scripts/init_db.py
cd frontend
npm ci
cd ..
```

For a classical-only starting environment, install `backend/requirements-core.txt` and `backend/requirements-dev.txt`. Install `backend/requirements-quantum.txt` before using quantum models and `backend/requirements-explainability.txt` before requesting SHAP. Permutation importance does not require SHAP.

## 5. Environment configuration and database setup

The backend reads `.env` from the **project root**, independently of terminal working directory. `QHEALTH_STORAGE_ROOT=.` stores the database and artifacts inside the project. Dataset CSVs live under `data/datasets`, trusted model bundles under `models`, and private experiment/report snapshots under `experiments`. A generated UUID is the only storage filename identity. `scripts/init_db.py` creates the schema; backend startup also initializes it idempotently.

`QHEALTH_API_TOKEN` is blank by default for loopback-only, single-user use. Before private-data work, generate a strong token locally and set it in `.env`; enter the same token in **Connection settings**. The browser keeps it in memory, never in local storage. An API token alone is not sufficient for public deployment. Do not place secrets in `VITE_*` variables. See [security](docs/security.md).

## 6. Backend startup

From the project root in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Linux/macOS:

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Health endpoint: `http://127.0.0.1:8000/api/health`. Generated OpenAPI schema: `http://127.0.0.1:8000/openapi.json`. Interactive API documentation: `http://127.0.0.1:8000/docs`. Use exactly one process: the MVP training worker is in-process. Avoid `--reload` while training.

## 7. Frontend startup

Open a second terminal in the project root:

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`; no frontend environment file is required. The connection indicator reports HTTP reachability, not scientific validity or quantum execution. `npm run build` performs a TypeScript check and production build when you execute it.

## 8. Docker startup

From the project root after copying `.env.example` to `.env`:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8080`. Both published ports are loopback-bound. Docker stores runtime data in a named volume. Stop with `docker compose down`; do not add `-v` unless intentionally deleting stored datasets and experiments. Docker images/configuration are provided, **not execution-verified**. See [deployment](docs/deployment.md).

## 9. Guided demo workflow

1. Open **Datasets** and select **Load Wisconsin benchmark**. Registration reads scikit-learn's packaged public dataset; it does not download arbitrary URLs. Verify source, hash, class counts, and the configured positive label **malignant**.
2. Open **Data quality**, then **Preprocessing**, **Feature selection**, and **PCA / dimensions**. Inspect descriptive quality and training-only previews. Defaults use 12 ANOVA-selected encoded features, four PCA components, and angle scaling shared by every model.
3. Open **Training**. Start with Logistic Regression, SVM and Random Forest. The default 160-sample stratified budget applies to every selected model, not just quantum models. A completed model's metrics appear only after actual fitting and held-out evaluation.
4. For a separate comparison, select classical baselines together with VQC and/or QSVC. Quantum selection requires shared PCA dimensions equal to qubits, shared angle scaling, no class weighting, and no calibration. Start with four qubits and modest optimizer iterations. Jobs expose state, partial failures, and cooperative cancellation.
5. Inspect **Model comparison**, **Quantum circuit**, and **Explainability**. In **Research prediction**, enter anonymous features or explicitly load one public demo sample. In **Experiments**, open a record and export its HTML or JSON report.

Optional CLI demonstration against an already-running server:

```powershell
.\.venv\Scripts\python.exe scripts\demo.py
.\.venv\Scripts\python.exe scripts\demo.py --quantum --max-samples 160
```

The second command performs genuine quantum training on your machine. No performance or runtime is promised.

## 10. Dataset upload and provenance

Only UTF-8 comma-separated `.csv` tables are supported, with one header row and at least ten records. Supply dataset name, domain, source/reference, version, target column, and explicit positive-class label. Confirm that records are de-identified and independent. The MVP requires exactly two nonmissing target labels; it rejects an absent target, invalid labels, invalid headers, binary files, oversized content, and unsupported extensions.

The database records the exact stored CSV SHA-256, upload time, rows/features, class distribution, source, version and class mapping. No upload is available through a static public URL. Uploaded raw records are not displayed globally. The public-demo sample endpoint explicitly refuses user-uploaded datasets.

## 11. Validation, preprocessing, feature selection and PCA

Quality reports show missing/infinite values, constants, low variance, high correlations, class imbalance, duplicates, potential identifiers, suspicious target proxies, and aggregate distributions. Mixed-type columns are reported as categorical rather than silently coerced to numeric. Identifiers, near-perfect proxies, contradictory duplicate vectors, and infinities block training until corrected or excluded.

Feature engineering supports configured nonnegative `log1p` transforms and numeric ratios. A zero denominator becomes missing and follows the training-fitted imputer. Numeric pipelines support median/mean/mode imputation, optional training-quantile clipping and standard/min-max/robust/no scaling. Categorical inputs use mode imputation and bounded one-hot encoding; public encoded-feature labels are neutralized to avoid disclosing category values.

Selection supports ANOVA, mutual information, variance threshold, or none. PCA and optional `[0, pi]` angle scaling are fitted only after the train/test split. Each CV fold receives a completely fresh full pipeline. Exact duplicate removal is explicit and documented; residual duplicate selected input vectors are rejected. See [ML pipeline](docs/ml_pipeline.md).

## 12. Classical and quantum ML

Classical models are Logistic Regression, SVM and Random Forest. Quantum models are VQC and QSVC behind a common sklearn-compatible adapter. VQC uses a ZZ feature map, real-amplitudes ansatz and COBYLA or SPSA. QSVC uses fidelity-kernel compute-uncompute. Backends are exact local statevector simulation or finite-shot Aer simulation with optional illustrative depolarizing noise.

**Quantum model** describes the estimator. **Hybrid quantum-classical method** describes classical preprocessing/optimization with quantum circuit evaluation. **Quantum simulation** executes locally on classical hardware. **Real quantum hardware** is not implemented or implied. The circuit view displays parameterized logical structure, not proof of hardware execution. See [quantum pipeline](docs/quantum_pipeline.md).

## 13. Benchmarking, evaluation and calibration

Every model in one experiment uses the same source hash, selected input schema, sampled rows, holdout indices, CV folds and transformation configuration. Comparison never combines arbitrary experiments with different conditions. Accuracy, precision, recall/sensitivity, specificity, F1, ROC-AUC, ROC curves and confusion matrices are calculated at runtime. FN/FP counts are explicit. Undefined metrics remain null, not invented zero scores.

Training resubstitution, CV mean/sample standard deviation and held-out test metrics are distinct. Training, CV and inference timings are measured separately. SVM/QSVC margins are not probabilities; therefore their uncalibrated predictions do not receive probability-based research risk categories. Optional classical-only sigmoid/isotonic calibration wraps the whole pipeline with inner training-only folds. Brier score and reliability curves are reported separately and never called clinical calibration.

## 14. Explainability and prediction

Permutation importance calculates measured ROC-AUC drops on a bounded held-out subset. Numeric, complete-input SHAP uses a bounded training-only background; mixed/missing-input datasets use permutation as the implemented alternative. Quantum explanations use finite-difference perturbation/sensitivity analysis in original feature space. Negative importance values remain visible. None of these methods establishes medical causation.

Prediction requires the exact registered input schema and an identified ready model. The screen distinguishes predicted class, positive-class model probability, decision score and non-clinical research risk category. Research thresholds are configurable. Sample inputs and predictions are not persisted. No diagnosis, treatment instruction, medical recommendation or patient prognosis is generated.

## 15. Experiments, model registry and API usage

Experiment records retain configuration, dataset provenance, split fingerprint, software versions, model metrics, timing and limitations. Models are tied to an experiment, source dataset, trusted artifact and its hash. Rerun creates a **new** experiment with `parent_id`; it never overwrites the original. Failed models remain visible. HTML/JSON reports include the medical disclaimer and measured, non-presumptive comparison text.

The API reference is [docs/api.md](docs/api.md). Public reachability is `GET /api/health`; other app endpoints accept an optional configured Bearer token. Training submission returns job and experiment records; poll `/api/training/jobs/{id}`. Reports are downloaded through the authenticated API, not a public file server.

## 16. Tests and source checks

Executable tests cover dataset/provenance, target quality, leakage boundaries, preprocessing, metrics, classical training, prediction schemas, security, API registries and report/rerun workflows. Quantum execution tests are deliberately opt-in. **These tests were generated and not run.**

```powershell
# From project root: static inspection only; does not import or execute the app.
.\.venv\Scripts\python.exe scripts\check_source.py
# Actual tests, to be run by you after installation:
cd backend
..\.venv\Scripts\python.exe -m pytest -m "not quantum"
$env:RUN_QUANTUM_TESTS="1"
..\.venv\Scripts\python.exe -m pytest -m quantum
cd ..\frontend
npm test
npm run build
```

See [testing](docs/testing.md). Synthetic arrays in test fixtures are assertions about code behavior, not demonstration performance or fabricated biomedical results.

## 17. Security considerations

Uploads are size/extension/header constrained and stored with generated IDs. Paths are validated, local artifact hashes are checked, raw biomedical payloads are not logged, and application errors omit request values. Uploaded code/models are never executed. Model persistence uses trusted local dill artifacts and is unsafe if an attacker can replace both artifacts and registry hashes. Protect the entire runtime directory.

This MVP has no multi-tenant accounts, RBAC, encryption-at-rest service, clinical audit certification, public-internet hardening or regulated deployment approval. Identifier-name heuristics are not complete de-identification. Use a controlled workstation and appropriate institutional policies. See [security](docs/security.md) before private-data work.

## 18. Troubleshooting and known limitations

- **Backend unavailable:** start both terminals; use the documented ports; inspect `/api/health`. A configured API token must be supplied in Connection settings after browser refresh.
- **Quantum unavailable/import errors:** install the optional quantum group in the same Python environment. Align actual installed versions with the documented API target; do not interpret availability detection as executed verification.
- **PCA/selection failure:** reduce components or choose more retained features/samples. Every CV training fold must support the dimensions; previews alone do not prove fold feasibility.
- **Quality blocks training:** correct or exclude identifiers/proxy features, resolve conflicting duplicates and infinities, and explicitly choose a duplicate policy. Do not simply suppress a leakage warning.
- **Permutation subset has one class:** increase explanation sample budget or use perturbation. SHAP is restricted to complete numeric raw features.
- **Slow quantum fit/cancellation:** lower the *shared* sample budget and optimizer iterations. Cancellation takes effect at safe boundaries, not in the middle of a simulator call. Do not start multiple backend workers.
- **Dependency/build failures:** compare the installed environment with [verified environment](docs/verified_environment.md). The recorded pins and lockfile cover dependency resolution, not Docker runtime or complete application execution.

See [limitations](docs/limitations.md) for unsupported grouped/time-series validation, privacy limitations, external validation gaps, unverified runtime behavior and finite-shot variability. No benchmark score establishes clinical validity, utility, regulatory approval or general quantum advantage.

## 19. Documentation map and dataset attribution

[Architecture](docs/architecture.md) | [API](docs/api.md) | [ML pipeline](docs/ml_pipeline.md) | [Quantum pipeline](docs/quantum_pipeline.md) | [Explainability](docs/explainability.md) | [Deployment](docs/deployment.md) | [Reproducibility](docs/reproducibility.md) | [Security](docs/security.md) | [Dataset provenance](docs/data_provenance.md) | [Requirements traceability](docs/requirements_traceability.md) | [Generation status](docs/generation_status.json)

The WDBC source is UCI Machine Learning Repository, DOI **10.24432/C5DW2B**, attributed to Wolberg, Mangasarian, Street and Street (1993), under **CC BY 4.0** as described by UCI. The actual application copy is reconstructed from the installed scikit-learn dataset and hashed at registration; the sklearn version and transformation are recorded. Original supplied specifications are retained under `docs/specifications/`.
