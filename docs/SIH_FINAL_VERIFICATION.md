# EntangleX Q-Health — Final SIH verification

**Repository:** `Itzx-kush/EntangleX-Q-Health_final`
**Historical verification date:** 2026-09-23
**Historical baseline reviewed:** `1ed30206f49635636ee763d3d43891564726f67b`
**Scope:** Final hardening pass for the existing FastAPI, SQLite, ML, quantum, provenance, storage, React, and SIH presentation architecture.

> The sections through “Remaining limitations” preserve the September 23 verification record. The dated dataset-library section appended below records the separate September 29 integration pass; historical results are not presented as newly executed evidence.

## Historical hardening changes

- Added focused frontend coverage for route fallback/active navigation, command palette search and keyboard activation, mobile drawer behavior, settings persistence, Demo Center stage navigation/readiness, and surfaced backend errors.
- Corrected Demo Center readiness so comparison, explainability, and prediction are not marked executable merely because any model record exists. They now require a completed experiment and at least one ready model; dataset-dependent stages stay `NOT YET RUN` without a registered dataset.
- Surfaced safe query and mutation errors on dataset, Demo Center, comparison, Quantum Lab, explainability, prediction, experiment registry, and experiment detail surfaces.
- Kept the scientific boundary explicit: local quantum simulation, measured benchmark outputs, research predictions, and feature influence only.
- Reviewed the existing responsive and reduced-motion rules. No new visual redesign or dependency version change was needed in this pass.

## Verification matrix

| Area | Result | Evidence |
|---|---|---|
| Pinned quantum imports | **PASS** | `qiskit==2.5.2`, `qiskit-machine-learning==0.9.1`, `qiskit-aer==0.17.2` imported successfully |
| Focused QNN suite | **PASS** | `RUN_QUANTUM_TESTS=1 pytest -q tests/test_qnn.py`: **12 passed** |
| Full backend regression with quantum enabled | **PASS** | `RUN_QUANTUM_TESTS=1 pytest -q`: **100 passed** |
| Frontend tests | **PASS** | `npm test`: **2 test files, 9 tests passed** |
| TypeScript and production build | **PASS** | `npm run build`: typecheck and Vite build passed |
| Live API smoke | **PASS** | Health, demo registration, validation, three previews, bounded training, comparison, explanation, prediction, circuit retrieval, experiment detail, and JSON report all returned expected success responses |
| Classical workflow | **PASS** | Bounded live experiment included logistic regression and produced a ready model |
| Quantum workflow | **PASS** | Bounded live experiment included QNN; job succeeded and circuit/prediction/explanation paths returned successfully |
| QNN workflow | **PASS** | Bounded live QNN run used 30 samples, 2 qubits, 5 optimizer iterations, local statevector simulation |
| Route HTTP smoke | **PASS** | `/`, `/datasets`, `/quality`, `/preprocessing`, `/features`, `/pca`, `/training`, `/comparison`, `/quantum`, `/explainability`, `/prediction`, `/experiments`, `/demo`, `/settings` each returned HTTP 200 from Vite |
| Frontend route rendering in a visible browser | **NOT VERIFIED** | Shared browser could not reach the local Vite server; see Browser QA |
| Responsive visual QA | **NOT VERIFIED** | Static breakpoint review completed; visible 1440/1280/1024/768/600/390 screenshots could not be captured in the shared browser |
| Accessibility audit | **PARTIAL** | Focused jsdom interaction coverage passed; axe/visible-browser audit was not available in this environment |
| Performance | **PASS WITH OBSERVATIONS** | Route splitting remains active; build emitted no >500 kB warning. Largest emitted JS chunk was about 425 kB raw / 117 kB gzip. |
| Repository hygiene | **PASS** | No secrets, `.env`, runtime DB, uploaded CSV, model artifact, log, `node_modules`, or build output is tracked; generated verification files are ignored |
| Scientific claim audit | **PASS** | Repository wording continues to reject quantum advantage, clinical validation, diagnosis, and patient-outcome claims |

## Exact commands

### Frontend

```bash
cd frontend
npm ci
npm test
npm run build
```

### Backend and quantum

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
RUN_QUANTUM_TESTS=1 pytest -q tests/test_qnn.py
RUN_QUANTUM_TESTS=1 pytest -q
```

The installed runtime reported:

```text
qiskit 2.5.2
qiskit_machine_learning 0.9.1
qiskit_aer 0.17.2
```

### Bounded live workflow

The live run used the local simulator and a small configuration: one classical model, one QNN, 30 samples, 2 qubits, 5 optimizer iterations, 2 CV folds, and 128 shots. It registered the public benchmark, validated it, previewed preprocessing/feature selection/PCA, trained both models, then exercised comparison, explanation, prediction, fitted circuit retrieval, experiment detail, and report export.

## Browser QA

Browser QA was attempted after starting both services with:

```bash
# backend
. .venv/bin/activate
QHEALTH_STORAGE_ROOT=/tmp/qhealth-browser python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

The local shell could reach both services (`curl` returned HTTP 200), and all requested route URLs returned HTTP 200. The shared `agent-browser` session returned `ERR_CONNECTION_REFUSED` for `127.0.0.1:5173` and timed out against the exposed sandbox address. Because the visible browser could not connect, interactive sidebar, drawer, command palette, settings, circuit viewer, forms, chart, mobile, and visual checks are explicitly **not verified**, not marked as passed.

## Documentation and demo readiness

- `docs/SIH_DEMO_VIDEO_SCRIPT.md` remains recording-ready and was checked against the current route names and actions. It correctly states that no video file exists.
- Demo Center readiness is now based on backend state rather than record existence alone.
- The product remains a research prototype. Benchmark classifications and research predictions are not diagnoses, treatment guidance, clinical validation, regulatory evidence, or evidence of general quantum advantage.

## Remaining limitations

1. Visible browser QA and screenshot-based responsive/visual review remain blocked by the sandbox browser network boundary.
2. Accessibility is not fully certified; the current pass has focused interaction tests but no completed visible axe audit.
3. Quantum runtime is local simulation only; `runtime_verified` remains false for real hardware, and no hardware credentials or hardware execution are used.
4. `npm audit` still reports two moderate advisories and the dependency install emits existing deprecation warnings; no unsafe forced upgrade was introduced.
5. External-cohort validation, clinical validation, regulatory review, fairness studies, and deployment hardening remain outside this repository pass.
6. No video was generated.

---

## Medical Dataset Library integration verification — 2026-09-29

**Branch:** `feature/dataset-e2e-validation`
**Baseline:** current `main` at `0ad21ae3e2a678f6c081788e0e9a9aea4bd17d1b`
**Scope:** integration, regression testing, and hardening of the Medical Dataset Library introduced after the historical verification above.

### Five-dataset verification

The parameterized integration suite exercised every packaged library entry through the same generic API and pipeline path:

1. Breast Cancer Wisconsin Diagnostic (`wdbc`)
2. Early Stage Diabetes Risk Prediction (`early-stage-diabetes`)
3. Heart Disease — Cleveland (`cleveland-heart-disease`)
4. Chronic Kidney Disease (`chronic-kidney-disease`)
5. ILPD Liver Patient Dataset (`ilpd-liver`)

For each entry, the executed tests verified resource readability, manifest SHA-256, row and feature counts, binary target labels, positive/negative labels, target presence, registration metadata, normalization metadata, built-in provenance, quality validation, preprocessing preview, feature-selection preview, PCA preview, and dataset-ID propagation. Each dataset then completed a bounded logistic-regression experiment with a fixed seed, two CV folds, and a maximum of 80 samples. The tests retrieved the experiment and model, exercised comparison, prediction, perturbation explanation, JSON report generation, and confirmed the model and experiment retained the selected dataset ID. No model metric is recorded in this document.

Breast Cancer was additionally checked through the legacy `POST /api/datasets/demo` workflow. The packaged library registration and legacy demo registration produced separate dataset IDs without changing their provenance semantics.

### Target detection and upload

The detector suite passed cases covering target-like names (`diagnosis`, `outcome`), binary and multiclass candidates, ID and timestamp penalties, continuous-measurement rejection, low-confidence/ambiguous candidates, missing targets, explicit target override, and explicit positive-label override.

The upload integration test performed inspection, automatic target detection, a manual override to a different binary target, explicit positive-label selection, independent final CSV validation, central registration, provenance retrieval, quality validation, and preprocessing preview. The registered target and positive label matched the final manual choices; inspection remained advisory.

### Dataset state hardening

- Switching built-in datasets now applies that dataset's recommended duplicate policy and clears only feature-dependent state (`features`, log features, and ratios), while preserving unrelated model configuration.
- Selecting a dataset immediately refreshes the displayed detail record rather than leaving stale metadata visible.
- Deleting the active dataset clears its persisted active ID and returns dataset-dependent draft state to safe defaults.
- A built-in public-license dataset no longer becomes a legacy demo dataset merely because it has license metadata. `is_demo=true` is now assigned only by the original approved `POST /api/datasets/demo` path, so `/api/models/{id}/demo-sample` remains restricted to that workflow. Models trained from Medical Dataset Library registrations receive HTTP 403 from that endpoint; a bounded model trained from the legacy demo registration successfully returned its approved demo sample.

### Quantum compatibility

All five datasets passed quantum configuration and shared-preprocessing validation with dataset-ID propagation, four PCA components, four qubits, and angle scaling enabled. This establishes configuration compatibility only.

One separate real, bounded simulator-backed QSVC experiment was executed for the packaged WDBC dataset with 30 samples, two qubits, two CV folds, 128 shots, and a five-iteration bound in the quantum configuration. The job succeeded and the resulting ready QSVC model retained the WDBC dataset ID. This executed test does not establish quantum advantage, clinical effectiveness, or hardware validation.

### Deployment and live HTTP verification

The packaged CSV resources remain under `backend/app/data/builtin_datasets` and are accessed through the package-resource catalog. The backend image copies the `app` source tree, so these resources are included in a fresh deployed artifact. Library listing reads manifest metadata; CSV bytes are read and verified when a dataset is selected. Registration creates runtime state only after selection and does not require a runtime download or persistent pre-seeded database.

A local Uvicorn process was exercised over real HTTP. The smoke run returned five library entries, registered CKD, retrieved registry/detail/provenance, validated quality, ran all three previews, inspected and registered a custom upload, and completed one bounded logistic-regression training job. The returned automatic upload target was `outcome`, and the job status was `succeeded`.

### Actual commands and results

```text
pytest -q tests/test_dataset_library.py tests/test_target_detection.py
31 passed, 1 skipped, 2 warnings in 7.37s

pytest -q
98 passed, 35 skipped, 2 warnings in 16.81s

RUN_QUANTUM_TESTS=1 pytest -q tests/test_dataset_library.py::test_wdbc_executes_one_bounded_real_qsvc_experiment
1 passed, 1 warning in 4.56s

npm test
2 test files passed; 17 tests passed in 5.06s

npm run build
tsc --noEmit passed; Vite production build completed in 5.16s
```

The default backend run skipped tests that explicitly require `RUN_QUANTUM_TESTS=1`; the one new bounded dataset-library QSVC integration test was then executed separately with that flag. Warnings were an existing FastAPI TestClient/httpx deprecation warning and a pandas future downcasting warning encountered by the CKD path.

### Current limitations

1. This pass did not complete visible-browser or screenshot-based responsive QA. Frontend behavior was verified with Vitest/jsdom, TypeScript checking, and the production build; no visual redesign was made.
2. Only WDBC received an executed quantum training check. The other four datasets received quantum configuration and preprocessing compatibility checks, not executed quantum training.
3. Quantum execution used a local simulator, not quantum hardware, and provides no evidence of quantum advantage.
4. The existing FastAPI/httpx and pandas warnings remain; dependency upgrades or unrelated transformer refactoring were intentionally excluded from this integration pass.

---

## SIH Demo Center / Judge Experience Integration — 2026-09-29

**Branch:** `feature/sih-demo-center-judge-flow`
**Baseline:** merged Prompt 3 `main` at `ee8d0956398bcc115817b01b5bf12a88a0da5d63`
**Scope:** frontend orchestration, truthful readiness, active dataset/experiment/model relationships, focused tests, and judge-flow documentation. The backend API and scientific pipeline were not changed.

### Judge workflow

The existing SIH Demo Center now provides a factual project introduction, a compact active-dataset summary, the latest experiment for that exact dataset, ready models from that exact experiment, a five-entry Medical Dataset Library quickstart, and direct actions for all eleven real application stages:

`Dataset → Quality → Preprocessing → Feature Engineering → PCA → Training → Classical / Quantum → Comparison → Explainability → Prediction → Report`

Every action uses an existing route. Dataset selection calls the existing built-in registration API and updates the existing persisted draft; it does not create another catalog or registry. The legacy `/api/datasets/demo` workflow is not called by the quickstart and remains separate.

### Truthful state matrix

The state derivation is isolated in `frontend/src/lib/demoState.ts` and covered as a pure function.

| Backend-backed context | Dataset | Configuration stages | Training | Comparison | Explainability / Prediction | Report |
|---|---|---|---|---|---|---|
| No valid active dataset | `NOT STARTED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` |
| Valid active dataset, no experiment | `READY` | `READY` | `READY` | `BLOCKED` | `BLOCKED` | `BLOCKED` |
| Current-dataset job active | `READY` | `READY` | `IN PROGRESS` | `BLOCKED` | `BLOCKED` | `BLOCKED` |
| Current experiment finished with one ready model | `READY` | `READY` | `COMPLETED` | `BLOCKED` | `READY` | `READY` |
| Current experiment finished with two or more ready models | `READY` | `READY` | `COMPLETED` | `READY` | `READY` | `READY` |

`READY` means the real next action is available; it never means a preprocessing, explanation, prediction, or comparison action was already executed. `COMPLETED` is reserved for persisted backend experiment/model state. A terminal experiment without a ready model is `BLOCKED`, not completed.

The latest experiment is selected only from records whose `dataset_id` matches the active validated dataset. Models must match both that dataset ID and the current experiment ID. Jobs must match the current experiment. Switching datasets therefore drops stale experiment/model readiness without deleting unrelated configuration.

### Scientific and legacy boundaries

- No metric, prediction, experiment, or readiness record is precomputed by the Demo Center.
- The UI states that benchmark output is research evidence, not clinical validation or diagnosis.
- Quantum capability is reported as local simulation unless the backend says otherwise; no quantum-advantage claim was added.
- Library selection uses `POST /api/datasets/library/{slug}`. It does not call `POST /api/datasets/demo` and does not alter `is_demo` or `/api/models/{id}/demo-sample` behavior.

### Tests and build

```text
npm test -- src/tests/demoState.test.ts src/tests/app.test.tsx
2 test files passed; 22 tests passed in 4.04s

npm test
3 test files passed; 25 tests passed in 4.67s

npm run build
tsc --noEmit passed; Vite production build passed in 4.61s

pytest -q
98 passed, 35 skipped, 2 warnings in 10.44s
```

Focused coverage includes the no-dataset matrix, valid-dataset configuration readiness, active jobs, latest-experiment selection over an older success, foreign experiment/model rejection, current completed experiment recognition, two-model comparison readiness, dataset-switch stale-state protection, all stage routes, one-click library selection, displayed backend metadata, legacy-demo non-use, and surfaced backend errors.

The backend warnings remain the existing FastAPI TestClient/httpx deprecation warning and pandas future downcasting warning on the CKD path. Quantum-only tests remained skipped in the default backend command because Prompt 4 did not change quantum execution.

### Local HTTP smoke

A real local Uvicorn server was exercised over HTTP. The run verified health, five-entry library discovery, WDBC library registration, dataset detail and provenance, `is_demo=false`, one bounded Logistic Regression job, experiment and model relationship IDs, a ready model, experiment detail, summary, and JSON report retrieval. The job status was `succeeded`, and the report dataset ID matched the registered active dataset ID.

### Deployment and QA limits

- Production frontend compilation succeeded and introduced no new runtime dependency or environment variable.
- Existing package-contained datasets and Docker copy behavior were unchanged; no runtime dataset download or database seed was introduced.
- Render itself was not redeployed or smoke-tested in this pass.
- Visible-browser and screenshot-based responsive QA were not performed, so they are not marked as passed. Existing jsdom interaction tests, route assertions, theme/mobile regression tests, and the production build passed.

## Prompt 5 — Verified instant demo readiness

The deployable backend now validates and hydrates two repository-packaged, genuine benchmark experiments on startup. See [Verified Instant Demo](VERIFIED_INSTANT_DEMO.md) for the exact dataset selection, immutable configuration, manifest layout, integrity checks, and operational boundary. The remaining three built-in datasets keep the complete live workflow and do not receive synthetic experiment or model records.

### Prompt 5 hardening

- Full manifest, dataset-byte, model SHA-256, safe-bundle, and relationship verification runs once per process and is retained in a fail-closed in-memory readiness cache. Normal library/readiness requests reuse verified metadata; tests and maintenance code can explicitly refresh the cache.
- Manifest schema v2 restores the genuine completed `Job` for each packaged experiment (`succeeded`, 100% progress, source final-state text, and source timestamps).
- Packaged model integrity is explicitly SHA-256 over decoded raw dill bytes. This is separate from the unchanged HMAC integrity used when normal live-trained models are saved at runtime.
- Uploaded/custom datasets resolve to `requires_processing` at the registered-dataset readiness boundary and remain eligible for the normal live pipeline. Public samples remain allowed for built-in benchmarks and the legacy demo, and blocked for uploaded datasets.

## Sensitivity-first operating point and evidence engine — 2026-09-30

This entry records a new implementation and executed verification pass. It does
not rewrite or supersede the historical records above.

### Implemented

- Added deterministic fixed and target-sensitivity research operating points.
- Sensitivity-first thresholds are selected only from training-partition
  out-of-fold validation scores, maximizing specificity with deterministic
  sensitivity/F1/threshold tie-breaks.
- The selected threshold is locked before final fitting and untouched holdout
  evaluation. Infeasible evidence returns no selected threshold.
- Persisted evidence includes threshold source, units, OOF curve, feasibility,
  validation/holdout metrics, OOF sample count, and CV fold count.
- Added structured quantum/classical performance, measured timing, logical
  resource, fairness, operating-point, limitation, and neutral-conclusion
  evidence while preserving the prior comparison delta fields.
- Added compact comparison tables, threshold trade-off rendering, active
  dataset/current-experiment defaults, explicit historical mode, and corrected
  “Validation, holdout, and runtime” terminology.

### Executed verification

- Targeted backend threshold/evidence/registry suite: **27 passed**, one
  pre-existing TestClient deprecation warning.
- Full non-quantum backend regression: **120 passed, 35 deselected**, two
  existing warnings.
- Optional simulator-backed quantum regression: **35 passed, 120 deselected**,
  15 warnings from bounded optimizer/deprecation paths.
- Focused sensitivity-first Logistic Regression + QNN API workflow, including
  comparison, prediction, and JSON report: **1 passed**.
- Frontend Vitest suite: **4 files, 32 tests passed**. jsdom emitted expected
  zero-size ResponsiveContainer warnings; no test failed.
- Frontend TypeScript check and Vite production build: **PASS**, 2,281 modules
  transformed.

The backend verification environment used Python 3.13 rather than the
repository's supported Python 3.11 baseline; the pinned dependency set
installed and the recorded suites passed. Visible-browser, Docker, Render, real
quantum hardware, external validation, clinical cutoff validation, robustness
benchmarking, and general quantum advantage were not verified or claimed in
this pass.

## Robustness and degradation evidence lab — 2026-09-30

This entry records the controlled Robustness Lab implementation and its
executed verification. It does not replace prior verification records.

### Implemented

- Added deterministic missingness, training-standard-deviation-scaled Gaussian
  noise, numerical outlier, and categorical corruption conditions.
- Conditions run on a bounded subset of the original held-out samples against
  frozen artifacts and locked operating thresholds. No fitting, threshold
  reselection, or training/CV mutation occurs.
- Persisted evidence includes dataset/split/model context, baseline and
  perturbed metrics, signed and relative changes, threshold provenance,
  timing, applicability status, condition fingerprints, and limitations.
- Classical and quantum models reuse one perturbed frame per condition.
  Existing comparison and report formats now expose paired robustness evidence
  while retaining legacy `not_evaluated` behavior.
- Added a judge-visible Robustness Lab with active-context filtering,
  bounded controls, actual delta visualization, explicit not-applicable states,
  and neutral language without winners, rankings, or advantage claims.

### Executed verification

- Targeted robustness, evidence, and route tests: **17 passed**, one existing
  TestClient deprecation warning.
- Full non-quantum backend regression: **124 passed, 35 deselected**, two
  existing warnings.
- Optional simulator-backed quantum regression, including a real paired
  Logistic Regression/QNN robustness request: **35 passed, 124 deselected**,
  15 bounded optimizer/deprecation warnings.
- Frontend Vitest suite: **4 files, 34 tests passed**. jsdom emitted expected
  zero-size ResponsiveContainer warnings; no test failed.
- Frontend TypeScript check and Vite production build: **PASS**, 2,281 modules
  transformed.

The perturbations are controlled synthetic benchmark conditions, not external
validation, hospital/population shift evidence, clinical robustness, patient
safety evidence, model ranking, or general quantum advantage. Docker, Render,
visible-browser responsive QA, and real quantum hardware were not exercised in
this pass.

## Adaptive quantum resource advisor — 2026-09-30

This entry records the resource-advisor implementation and executed
verification without replacing earlier evidence.

### Implemented

- Added canonical policy `bounded-simulator-resource-policy-v1`, with validated
  schema bounds, explicit single-workstation thresholds, near-budget semantics,
  and a deterministic reduction order.
- Added interpretable circuit, optimization, measurement, sample, backend, and
  noise dimensions without a black-box score or fabricated runtime estimate.
- Added valid smaller configuration recommendations checked through
  `TrainingConfig`, including qubit/PCA compatibility. Recommendations require
  an explicit Apply action and never start training.
- Added historical evidence from recorded ready-model timing/resource fields
  using exact model/backend/qubit matching. Missing history returns null timing
  rather than an estimate.
- Added policy/advisor APIs and integrated the workflow into Quantum Lab with
  observed-history and real-hardware limitation messaging.

### Executed verification

- Advisor-specific backend suite: **7 passed**, one existing TestClient
  deprecation warning.
- Targeted advisor, threshold/evidence, and robustness regression:
  **18 passed**, one existing warning.
- Full non-quantum backend regression: **131 passed, 35 deselected**, two
  existing warnings.
- Optional simulator-backed quantum regression: **35 passed, 131 deselected**,
  15 bounded optimizer/deprecation warnings.
- Frontend Vitest suite: **4 files, 36 tests passed**. Existing jsdom
  ResponsiveContainer size warnings remained non-failing.
- Frontend TypeScript check and Vite production build: **PASS**, 2,281 modules
  transformed.
- Static Python/JSON source validation and diff whitespace check: **PASS**.

The advisor does not execute circuits, predict model quality, estimate
wall-clock time for unseen requests, or infer QPU performance. Docker, Render,
visible-browser responsive QA, and real quantum hardware were not exercised.
