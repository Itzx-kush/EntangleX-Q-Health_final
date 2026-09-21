# Generated automated tests

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

## Separate verification levels

`python scripts/check_source.py` parses Python/JSON and checks required files without importing the application. That is a static inspection, not tests. Frontend source parsing is also not a dependency-resolved type check or browser render. Passing local unit tests would still not independently establish Docker compatibility, end-to-end UI connectivity, clinical validity or model generalization. Verify each layer separately and record exact commands/environment/results.
