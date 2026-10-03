# Generated automated tests

## Current Task 1 verification

The opening statement below describes the original source-generation phase. Post-generation Task 1 verification ran the complete backend suite with quantum tests enabled (`67 passed, 11 warnings`), targeted security/storage/data-quality tests (`32 passed, 2 warnings`), and the frontend `npm ci`, typecheck, Vitest suite (`3 files / 6 tests`), and production build. A bounded live backend smoke also passed. Docker was not executed because the final verification environment did not provide the Docker CLI/daemon. See [Task 1 final verification](task1_final_verification.md).

**No automated test was executed during project generation. No passing test claim is made.** The files are executable tests for the user to run after resolving dependencies in an isolated environment.

## Backend coverage

`test_data_quality.py` covers CSV parsing, target validation, source hashes, demo label orientation/provenance, missing/infinite values, class imbalance, identifier/proxy detection and category privacy. `test_pipeline_and_leakage.py` covers disjoint reproducible partitions, train-only imputation statistics, fresh CV pipeline clones, PCA previews, quantum dimension constraints and category-label redaction. `test_metrics_and_prediction.py` covers manually checkable confusion counts, sensitivity/specificity, undefined metrics, CV standard deviation, positive-probability orientation, margin-only behavior and prediction schema validation.

`test_security_and_api.py` covers UUID paths, sanitization, artifact integrity, origin/token checks, non-echoed validation errors, absent model-upload support, aggregate dataset output and upload body limits. `test_training_and_registry.py` actually trains bounded classical models and provides a local HTTP integration test covering job creation/polling, registry/provenance, prediction, report export, protected source retention and immutable rerun links. `test_quantum_optional.py` builds actual circuits and performs tiny genuine VQC/QSVC fits only when explicitly enabled.

The conftest sets a temporary storage root before application imports and removes it at session teardown. It does not use the user's normal runtime directory. Synthetic fixtures are test inputs with known properties; they are not application demonstration results, biomedical evidence or fabricated quantum metrics.

## Commands

From the project root, use the matching virtual-environment Python executable:

```bash
cd backend
../.venv/bin/python -m pytest -m 'not quantum'
RUN_QUANTUM_TESTS=1 ../.venv/bin/python -m pytest -m quantum
cd ../frontend
npm test
npm run build
```

Windows PowerShell variants are in the README. Quantum tests are opt-in because they perform genuine simulator work and require the optional packages. Skipping them does not count as verified quantum execution. The integration test has a bounded polling timeout and reports timeout/failure rather than manufacturing a completed job.

Frontend tests cover absent-measurement formatting, zero-valued metrics, job states, the visible disclaimer and in-memory token transport without local-storage persistence. The production build additionally runs TypeScript checking when dependencies are installed.

## Operating-point and evidence coverage

`test_thresholds_and_evidence.py` covers fixed-threshold compatibility,
validation-only sensitivity-first selection, specificity maximization,
deterministic tie-breaking, truthful infeasibility, locked holdout evaluation,
performance/timing deltas, logical quantum-resource extraction, missing legacy
metadata, neutral conclusions, and unfavorable quantum results.

The training/registry regression checks persisted operating points and
same-seed rerun reproducibility. Frontend interaction coverage checks strategy
and target controls, selected and infeasible operating points, evidence and
resource rendering, active-context filtering, historical-record access,
scientific limitations, and the corrected “Validation, holdout, and runtime”
terminology.

## Robustness and degradation coverage

`test_robustness.py` covers deterministic seeded perturbations, realized
missingness, Gaussian noise, numerical outliers, categorical corruption,
explicit not-applicable conditions, undefined relative metrics, signed deltas,
bounded sample counts, persisted history, locked-threshold preservation,
baseline reproduction, shared perturbation fingerprints, and a guard that
fails if the endpoint attempts to call the fitted pipeline's training method.

The optional QNN end-to-end test exercises one real paired classical/quantum
Gaussian-noise condition and verifies that the existing comparison evidence
object exposes the stored robustness scenario without ranking either model.
Frontend interaction tests cover scenario/model selection, request execution,
baseline/perturbed/delta rendering, paired neutral language, and explicit
not-applicable display.

## Quantum resource-advisor coverage

`test_resource_advisor.py` covers within-, near-, and over-budget states;
deterministic profiles and recommendations; canonical schema/policy bounds;
unchanged input objects; recommendation order; validation through
`TrainingConfig`; PCA/qubit compatibility; statevector shot semantics; explicit
simulator/hardware separation; malformed API inputs; policy versioning; real
recorded history aggregation; and the no-history/null-timing state. Tests also
assert that no fabricated `estimated_runtime` field exists.

Frontend coverage renders resource and budget states, changed parameters,
actual historical timing, no-history messaging, and the hardware limitation.
It verifies that the draft remains unchanged after analysis and changes only
after the explicit Apply action, including synchronized qubit/PCA dimensions
and bounded sample count.

## Separate verification levels

`python scripts/check_source.py` parses Python/JSON and checks required files without importing the application. That is a static inspection, not tests. Frontend source parsing is also not a dependency-resolved type check or browser render. Passing local unit tests does not independently establish Docker compatibility, clinical validity or model generalization. The post-generation Task 1 records separately document the native backend/frontend runtime checks and the Docker limitation.

## Executable hybrid validation (2026-09-30)

Focused tests execute an unmocked PennyLane QNode and PyTorch head, verify quantum-weight updates, cloneability, deterministic seeded behavior, valid probabilities, expectation outputs, and restricted-artifact round trips. The bounded end-to-end smoke registers the existing `early-stage-diabetes` catalog dataset and uses 40 shared samples, 2 PCA components/qubits, 1 quantum layer, one 4-unit classical hidden layer, 5 epochs, batch size 8, 2 CV folds, and target-sensitivity thresholding. It trains Random Forest and the hybrid model on the same split, then exercises persistence, prediction, mixed-type SHAP, and comparison evidence. Test measurements are not clinical claims.

## Hybrid SHAP refinement validation (2026-09-30)

Tests cover the real persisted Early Stage Diabetes hybrid artifact, exact-case prediction SHAP, global SHAP, original names/values, signed directions, OOF-threshold context, mixed categorical/numeric reconstruction, unseen-category and missing-feature failures, unavailable/failing SHAP behavior, and no-placeholder guarantees. Frontend tests assert that hybrid method state visibly reads `SHAP — Final Hybrid Output`, never presents permutation as the executed method, and renders positive/negative groups, probability, threshold, original values, and the causality limitation.

## Fair benchmark validation

Comparison tests cover matching and mismatching dataset hashes, sample pools, splits, PCA/qubit dimensions, sample budgets, seeds, CV folds, and threshold strategies. They also verify neutral deltas, null-preserving metrics, measured timing, `default.qubit` metadata, persistence, paired robustness fingerprints, report export, and the absence of ranking claims. The bounded diabetes integration test executes the real PennyLane + PyTorch training path when hybrid dependencies are installed; it is not replaced with a mocked estimator.

## Scientific CI verification

`python -m app.verification` runs the Scientific CI gate that verifies reproducibility, immutability,
migration, deployment-import and scientific contract invariants independently of the test suite.
The pull-request gate is the `fast` profile; the nightly and manual runs use the `full` profile.
See [Scientific CI verification](scientific_ci_verification.md) for the check registry, severity
semantics, fixtures and local commands.
