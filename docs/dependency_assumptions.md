# Dependency assumptions and external API references

**Generated on 2026-09-10. None of these dependency combinations was installed or execution-tested during source generation.** These are implementation targets, not a compatibility certification or frozen environment.

| Component | Declared target | Manifest |
|---|---|---|
| Python | 64-bit 3.11 | README / Dockerfile |
| FastAPI / Pydantic | FastAPI >=0.115,<1; Pydantic >=2.10,<3 | requirements-core.txt |
| Pydantic settings | >=2.7,<3 | requirements-core.txt |
| SQLAlchemy | >=2.0.36,<2.1 | requirements-core.txt |
| NumPy / pandas / SciPy | >=2,<3 / >=2.2,<3 / >=1.13,<2 | requirements-core.txt |
| scikit-learn | >=1.6,<2 | requirements-core.txt |
| SHAP | >=0.47,<1 | requirements-explainability.txt |
| Qiskit | >=2.1,<3 | requirements-quantum.txt |
| Qiskit Machine Learning | 0.9.1 | requirements-quantum.txt |
| Qiskit Aer | >=0.17.1,<0.18 | requirements-quantum.txt |
| React / React DOM | ^19.1.0 | frontend/package.json |
| TypeScript / Vite | ~5.9.2 / ^7.1.0 | frontend/package.json |
| Node | >=22.12; Docker Node 22 | frontend/package.json / Dockerfile |

Bounded ranges are deliberately honest about unresolved transitive dependencies. Broad ranges can drift: resolve in a clean environment, run the generated tests and builds, then record exact versions. No package-lock file was fabricated. `npm install` creates a real local lockfile. Docker currently resolves from the manifests; for repeatable deployment, preserve a verified lockfile and switch the frontend install step to `npm ci` only once that real lockfile exists and is copied into the build.

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

These references support the selected APIs, not the claim that this particular assembled application works. Quantum adapter updates should remain isolated in `backend/app/quantum`. Confirm QMLSampler seeding, optimizer namespace, pass manager behavior, Aer options, and object serialization against your actually installed environment.

## Verification responsibilities after installation

Record `python --version`, `node --version`, `python -m pip freeze`, and `npm ls --depth=0`. Run backend tests, opt-in quantum tests, TypeScript/build checks, frontend tests, then the guided API/UI workflow and Docker deployment separately. Do not infer any of those outcomes from source generation or static parsing alone.
