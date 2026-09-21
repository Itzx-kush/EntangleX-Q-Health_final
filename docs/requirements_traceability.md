# Requirements-to-source traceability

Status here means **implemented in generated source**, not runtime verified. Both supplied specifications are retained in `specifications/` and remain authoritative; biomedical constraints take precedence. No missing upstream generic specification is assumed.

| Requirement group | Primary implementation |
|---|---|
| Modular FastAPI, Pydantic, SQLAlchemy/SQLite | `backend/app/main.py`, `api/`, `database.py`, `storage/entities.py` |
| Dashboard and biomedical research positioning | `frontend/src/pages/Dashboard.tsx`, `components/Common.tsx`, `App.tsx` |
| Dataset upload/management/provenance | `data/service.py`, `api/datasets.py`, `pages/Datasets.tsx` |
| Quality, target validation, imbalance, identifiers | `data/quality.py`, `pages/Quality.tsx` |
| Leakage-safe train/test and fold-local preprocessing | `data/splitting.py`, `feature_engineering/pipeline.py`, `models/training.py` |
| Ratios/logs, imputation, encoding, scaling/outliers | `feature_engineering/transformers.py`, `pages/Preprocessing.tsx` |
| Feature selection and PCA | `feature_engineering/pipeline.py`, `pages/FeatureSelection.tsx`, `pages/PCA.tsx` |
| LR, SVM, Random Forest | `models/factory.py`, `models/training.py` |
| Quantum backend, VQC, QSVC, feature map/ansatz/noise | `quantum/backends.py`, `quantum/estimator.py`, `quantum/circuits.py` |
| Quantum configuration and circuit screen | `components/QuantumSettings.tsx`, `pages/QuantumCircuit.tsx` |
| Training jobs, status/failure/cancellation | `jobs/manager.py`, `api/training.py`, `pages/Training.tsx` |
| Sensitivity, specificity, FN/FP, ROC-AUC and timing | `evaluation/metrics.py`, `models/training.py`, `components/Common.tsx` |
| CV means/std vs held-out and training | `evaluation/metrics.py`, `pages/Comparison.tsx` |
| Calibration architecture and separate diagnostics | `evaluation/calibration.py`, `evaluation/metrics.py` |
| Equivalent-condition comparison/no presumed advantage | `experiments/comparison.py`, `pages/Comparison.tsx` |
| Classical SHAP/permutation, quantum perturbation | `explainability/service.py`, `models/prediction.py`, `pages/Explainability.tsx` |
| Safe research prediction/probability/category terminology | `models/prediction.py`, `api/models.py`, `pages/Prediction.tsx` |
| Experiment/model registries and rerun lineage | `storage/entities.py`, `api/experiments.py`, `pages/Experiments.tsx` |
| Reports, measured conclusion and disclaimer | `experiments/reports.py`, `pages/ExperimentDetail.tsx` |
| Upload size, paths, no raw logs, no secret literals | `api/middleware.py`, `api/security.py`, `storage/files.py`, `.env.example` |
| Demo without fake results or identifiers | `data/service.py:register_demo`, `scripts/demo.py` |
| Docker and exact startup commands | Dockerfiles, `docker-compose.yml`, README |
| Executable tests, including optional genuine quantum | `backend/tests/`, `frontend/src/tests/` |
| Biomedical limits, source provenance, dependency assumptions | `docs/limitations.md`, `data_provenance.md`, `dependency_assumptions.md` |

## Explicit minor implementation choices

The source asks for reasonable MVP choices where unspecified. Those choices are a bounded in-process worker rather than Redis/Celery, CSV-only upload rather than arbitrary spreadsheets, SQLite JSON metadata, React/Vite without a component-library dependency, local statevector/Aer simulation without real hardware credentials, HTML/JSON report exports, four-qubit/160-sample defaults, API token optional for loopback-only use, and no invented lockfile. Defaults are configurable where applicable and are not performance promises.

## Explicit functional limits

Calibration is implemented for classical-only experiments. SHAP is restricted to complete numeric raw inputs in this implementation. Quantum explanations use perturbation rather than inventing an internal circuit interpretation. Dependence/group/time-aware validation, real hardware, multi-tenant deployment, medical certification and PDF export are not represented as implemented features. These do not change the supplied binary-benchmark research positioning.
