# Verified environment

**Verification date:** 2026-09-21  
**Scope:** dependency installation, import compatibility, and package-resolution verification only.

This record does **not** certify the complete application, backend/frontend integration, Docker runtime, model training, quantum execution, or clinical validity. The exact commands and remaining limits are listed below.

## Runtime versions

| Tool | Verified version |
|---|---|
| Python | CPython 3.11.16 |
| Node.js | v22.12.0 |
| npm | 10.9.0 |

The repository targets the Node 22.x line through `.nvmrc`, `frontend/package.json`, and the pinned build-stage image in `frontend/Dockerfile`.

## Python environment

The clean environment was created with:

```bash
python3.11 -m venv .venv311
.venv311/bin/python -m pip install --upgrade pip
.venv311/bin/python -m pip install -r backend/requirements.txt
```

The direct requirements are pinned in `backend/requirements-*.txt`. The complete resolved Linux/Python 3.11 freeze was:

```text
PyYAML==6.0.3
Pygments==2.21.0
SQLAlchemy==2.0.54
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
certifi==2026.7.22
click==8.5.0
cloudpickle==3.1.2
dill==0.4.1
fastapi==0.141.1
greenlet==3.5.6
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.20
iniconfig==2.3.0
joblib==1.6.0
llvmlite==0.49.0
narwhals==2.26.0
numba==0.67.0
numpy==2.4.6
packaging==26.3
pandas==2.3.3
pluggy==1.6.0
psutil==7.2.2
pydantic==2.13.5
pydantic-core==2.46.5
pydantic-settings==2.15.0
pytest==8.4.2
python-dateutil==2.9.0.post0
python-dotenv==1.2.3
python-multipart==0.0.32
pytz==2026.3.post1
qiskit==2.5.2
qiskit-aer==0.17.2
qiskit-machine-learning==0.9.1
rustworkx==0.18.1
scikit-learn==1.9.1
scipy==1.17.1
shap==0.51.0
six==1.17.0
slicer==0.0.8
starlette==1.6.0
stevedore==5.9.1
threadpoolctl==3.7.0
tqdm==4.70.1
typing-extensions==4.16.0
typing-inspection==0.4.4
tzdata==2026.4
uvicorn==0.53.0
uvloop==0.22.1
watchfiles==1.3.0
websockets==17.1
```

## Python checks

The following passed:

- Import of FastAPI, Pydantic, pydantic-settings, SQLAlchemy, NumPy, pandas, SciPy, scikit-learn, pytest, Qiskit, Qiskit Machine Learning, Qiskit Aer, and SHAP.
- Import of `app.main` and the existing quantum adapter modules with `PYTHONPATH=backend`.
- Construction of the existing Qiskit feature-map, ansatz, QMLSampler, Aer SamplerV2, ComputeUncompute, fidelity-kernel, and pass-manager objects.

No model training or quantum circuit execution was performed for this task.

## Frontend environment

The existing `frontend/package-lock.json` was valid and matched `frontend/package.json`. A clean installation passed with:

```bash
node --version
npm --version
npm ci --prefix frontend --ignore-scripts
npm ls --prefix frontend --depth=0
```

Resolved direct packages:

| Package | Version |
|---|---|
| React | 19.3.0 |
| React DOM | 19.3.0 |
| React Router DOM | 7.18.3 |
| TypeScript | 5.9.3 |
| Vite | 7.3.6 |
| Vitest | 3.2.7 |
| `@testing-library/react` | 16.3.3 |
| `@testing-library/jest-dom` | 6.9.1 |
| `@types/react` | 19.3.0 |
| `@types/react-dom` | 19.3.0 |
| `@vitejs/plugin-react` | 4.7.0 |
| `jsdom` | 26.1.0 |

The npm audit reported two moderate-severity advisories in the resolved tree. No audit-driven upgrade was applied because it could change the verified dependency set and is outside this stabilization task.

## Verification status

| Check | Status |
|---|---|
| Fresh Python 3.11 environment creation | PASS |
| Python dependency installation | PASS |
| Major Python and application imports | PASS |
| Qiskit API construction compatibility | PASS |
| Clean npm installation from committed lockfile | PASS |
| Frontend dependency resolution | PASS |
| Exact package versions recorded | PASS |
| Backend test suite | PASS — 67 passed with quantum tests enabled |
| Frontend test suite/typecheck/build | PASS — 3 files/6 tests; typecheck and build passed |
| Backend/frontend integration | PASS — native API boundary and live smoke |
| Docker build/runtime | NOT PERFORMED — Docker unavailable |
| Classical or quantum model execution | PASS — bounded classical, VQC, QSVC and simulator checks |

The table above is the current post-generation status. The original dependency-only verification intentionally stopped before application runtime; its historical boundary is preserved in the surrounding record.