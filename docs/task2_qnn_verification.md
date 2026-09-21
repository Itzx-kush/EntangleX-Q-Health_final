# Task 2 QNN Verification

**Verification date:** 2026-09-21
**Repository:** `Itzx-kush/EntangleX-Q-Health_final`
**Starting baseline:** `67da36d6092740dacde27e8fd60dfda97b3540e1`
**Scope:** additive QNN support only. Task 1 was not redone, Task 3 was not started, and Docker runtime was not claimed.

## Scope

Task 2 adds a genuine QNN to the existing hybrid quantum-classical training architecture:

```text
shared split
  -> fold-local preprocessing
  -> feature selection
  -> PCA
  -> angle scaling
  -> sklearn-compatible QNN adapter
  -> measured evaluation, persistence, registry and API workflows
```

No new persistence system, database architecture, quantum framework, or frontend redesign was introduced.

## Existing Models Preserved

- Logistic Regression preserved.
- SVM preserved.
- Random Forest preserved.
- VQC preserved.
- QSVC preserved.
- QNN added under the exact identifier `qnn`.

QNN is not evidence of quantum advantage. QNN execution in this implementation uses local simulation; no real quantum hardware execution was implemented or verified.

## QNN Architecture

- **Adapter:** `QuantumClassifier(kind="qnn")` in `backend/app/quantum/estimator.py`.
- **Primitive:** Qiskit Machine Learning `SamplerQNN` with `NeuralNetworkClassifier`.
- **Feature map:** the existing ZZ feature map from `backend/app/quantum/circuits.py`.
- **Ansatz:** the existing real-amplitudes ansatz.
- **Trainable parameters:** ansatz parameters, recorded in `quantum_metadata_["trainable_parameter_count"]`.
- **Optimizer:** existing `COBYLA` or `SPSA` selection, bounded by `QuantumConfig.maxiter`.
- **Seed handling:** existing training seed controls Qiskit algorithm globals, sampler construction and deterministic initial ansatz weights.
- **Output semantics:** computational-basis probabilities are parity-aggregated into class 0 and class 1 by `SamplerQNN`. `predict_proba` returns the measured two-class probability vector; `decision_function` is the positive-class probability minus 0.5. These are model outputs, not clinical risk.
- **Persistence:** the existing trusted dill artifact bundle and SHA-256 verification are unchanged.
- **Registry:** QNN is persisted as a normal `ModelRecord` with `model_type="qnn"` and existing metrics/details.
- **API:** QNN is accepted by training configuration, circuit preview, training jobs, model prediction, circuit retrieval, comparison and reports.
- **Circuit metadata:** QNN circuit descriptions include the composed feature map and ansatz, backend/execution kind, qubit count, logical depth, gate counts, parameter count, text and limitations. Circuit structure is not hardware performance.

QNN uses the same quantum safety boundaries as VQC/QSVC: quantum dependencies are required, qubit/PCA dimensions must agree, angle scaling remains enabled, class weighting and calibration are rejected, and no silent fallback is performed.

## Verification Performed

The focused suite in `backend/tests/test_qnn.py` passed **12 tests, 0 failures**:

- dependency imports and pinned Qiskit Machine Learning APIs
- primitive/classifier construction
- input-dimension and binary-label validation
- deterministic small fit and prediction
- probability normalization and score semantics
- QNN circuit metadata
- artifact persistence, hash-backed reload and prediction after reload
- invalid configuration handling
- controlled missing-dependency error behavior
- circuit API smoke
- shared preprocessing/training pipeline
- training job, model registry, prediction, comparison and report integration

The complete backend suite with quantum tests enabled passed **79 tests, 0 failures, 16 warnings**.

The live bounded API smoke passed:

- health and OpenAPI
- quantum capability discovery
- demo dataset registration
- QNN plus Logistic Regression training job
- successful QNN model registration
- fitted QNN circuit retrieval
- comparison endpoint
- HTML report endpoint

## Regression

| Area | Result |
|---|---|
| Logistic Regression | PASS — full backend regression |
| SVM | PASS — full backend regression |
| Random Forest | PASS — full backend regression |
| VQC | PASS — existing quantum regression |
| QSVC | PASS — existing quantum regression |
| QNN focused tests | PASS — 12 passed |
| Backend regression | PASS — 79 passed, 0 failed |
| Frontend typecheck | PASS |
| Frontend tests | PASS — 3 files, 6 tests |
| Frontend production build | PASS |
| Live QNN API smoke | PASS |
| Persistence/reload | PASS — focused QNN test |
| Circuit API | PASS — focused QNN test and live smoke |
| Experiment/report/comparison | PASS — focused QNN integration test and live smoke |

The implementation was exercised in the isolated workspace with the pinned package versions Qiskit 2.5.2, Qiskit Machine Learning 0.9.1 and Qiskit Aer 0.17.2. The workspace runtime was CPython 3.13.14; the repository’s supported and previously verified baseline remains CPython 3.11.16. No dependency upgrade was made for QNN.

## Known Warnings

- The bounded five-evaluation COBYLA smoke configuration is below SciPy’s recommended `num_vars + 2` minimum, so SciPy emits a non-failing `MAXFUN` warning and clamps the effective minimum.
- Existing Qiskit VQC and scikit-learn SVC compatibility/deprecation warnings remain.
- Existing Starlette/TestClient and AnyIO deprecation warnings remain.
- npm reported the sandbox’s Node 24 runtime is outside the repository’s Node 22 engine range; typecheck, tests and build still passed.
- Docker build/runtime was not performed because Docker was unavailable in the environment.

## Genuine Remaining Limitations

- Execution is local simulator execution only; no hardware execution is claimed.
- Optimizer iterations and simulator sample counts are intentionally bounded.
- Finite-shot Aer runs can be stochastic.
- No clinical validation, external-cohort validation, regulatory approval or medical diagnosis is claimed.
- QNN results do not establish quantum advantage or statistical superiority.
- Benchmark metrics are measured at runtime only; this document contains no fabricated QNN performance numbers.

## Scientific Boundary

QNN output is a research-model probability or decision score. A model probability is not clinical risk, feature influence is not medical causation, simulation is not hardware, and a single seed is not statistical proof. The application remains a research prototype.
