# Dependency assumptions and external API references

**Dependency verification date:** 2026-09-21. The direct dependency manifests and the committed frontend lockfile were installed and checked in clean environments. This is an environment compatibility record, not a certification of the complete application or model execution. See [verified environment](verified_environment.md) for exact resolved versions and commands.

## Verified direct dependencies

| Component | Verified version | Manifest |
|---|---:|---|
| Python | CPython 3.11.16 | `backend/Dockerfile` |
| FastAPI | 0.141.1 | `backend/requirements-core.txt` |
| Uvicorn | 0.53.0 | `backend/requirements-core.txt` |
| Pydantic / pydantic-settings | 2.13.5 / 2.15.0 | `backend/requirements-core.txt` |
| SQLAlchemy | 2.0.54 | `backend/requirements-core.txt` |
| NumPy / pandas / SciPy | 2.4.6 / 2.3.3 / 1.17.1 | `backend/requirements-core.txt` |
| scikit-learn | 1.9.1 | `backend/requirements-core.txt` |
| SHAP | 0.51.0 | `backend/requirements-explainability.txt` |
| Qiskit | 2.5.2 | `backend/requirements-quantum.txt` |
| Qiskit Machine Learning | 0.9.1 | `backend/requirements-quantum.txt` |
| Qiskit Aer | 0.17.2 | `backend/requirements-quantum.txt` |
| pytest / httpx | 8.4.2 / 0.28.1 | `backend/requirements-dev.txt` |
| Node.js / npm | 22.12.0 / 10.9.0 | `.nvmrc`, `frontend/Dockerfile` |
| React / React DOM | 19.3.0 / 19.3.0 | `frontend/package.json`, `frontend/package-lock.json` |
| React Router DOM | 7.18.3 | `frontend/package.json`, `frontend/package-lock.json` |
| TypeScript / Vite / Vitest | 5.9.3 / 7.3.6 / 3.2.7 | `frontend/package.json`, `frontend/package-lock.json` |

The Python pins form one verified Python 3.11-compatible set. Qiskit Machine Learning 0.9.1, Qiskit 2.5.2, and Qiskit Aer 0.17.2 successfully imported together, and the existing adapter's Qiskit objects were constructible. Quantum training and execution were intentionally not performed here.

The frontend lockfile was already present, valid, and consistent with `frontend/package.json`; it was preserved and is used by both local setup (`npm ci`) and the Docker build. No package-manager migration was made.

## Node version policy

The supported Node runtime is the **22.x line starting at 22.12.0**:

- `.nvmrc` selects `22.12.0`.
- `frontend/package.json` requires `>=22.12.0 <23`.
- `frontend/Dockerfile` uses `node:22.12.0-alpine`.
- The README installation instructions use `npm ci`.

## Official references consulted for implementation decisions

- VQC sampler, optimizer and pass manager API: https://qiskit-community.github.io/qiskit-machine-learning/stubs/qiskit_machine_learning.algorithms.VQC.html
- QMLSampler, including analytic `shots=None`: https://qiskit-community.github.io/qiskit-machine-learning/stubs/qiskit_machine_learning.primitives.QMLSampler.html
- ComputeUncompute: https://qiskit-community.github.io/qiskit-machine-learning/stubs/qiskit_machine_learning.state_fidelities.ComputeUncompute.html
- Qiskit ML published release: https://pypi.org/project/qiskit-machine-learning/
- Qiskit ML 0.9.1 upstream requirements: https://raw.githubusercontent.com/qiskit-community/qiskit-machine-learning/0.9.1/requirements.txt
- Aer SamplerV2: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.primitives.SamplerV2.html
- Functional ZZ feature map: https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.zz_feature_map
- sklearn calibrated classifier: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
- SHAP Explainer: https://shap.readthedocs.io/en/latest/generated/shap.Explainer.html
- Vite Node requirements: https://vite.dev/guide/

## Remaining verification responsibilities

Run the backend tests, opt-in quantum tests, TypeScript/build checks, frontend tests, guided API/UI workflow, and Docker deployment separately. Do not infer those outcomes from this dependency verification.
