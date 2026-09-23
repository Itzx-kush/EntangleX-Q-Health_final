# EntangleX Q-Health — SIH Demo Script

This script uses the live product. Do not present a metric, status, or quantum capability
unless the backend has returned it during the run.

| Time | Screen | What to say |
|---|---|---|
| 00:00 | SIH Demo Center | “Biomedical risk research needs reproducible, interpretable evaluation rather than a single opaque score.” |
| 00:20 | Overview | “Q-Health connects data evidence, preprocessing, classical ML, quantum ML, controlled evaluation, explainability, and research prediction.” |
| 00:45 | Datasets | Load the public Wisconsin benchmark or an authorized deidentified CSV. Show source, hash, target, class mapping, and row/feature counts. |
| 01:20 | Data quality | Show missingness, class balance, duplicates, identifier/proxy warnings, and whether training is blocked. |
| 01:45 | Preprocessing → Features → PCA | Show training-only transformations, selection, PCA dimensions, and the shared representation used for comparison. |
| 02:20 | Training | Select classical baselines. Explain that the job state and results come from the real backend worker. |
| 02:50 | Quantum Lab | Show the logical circuit view and explain local simulation, qubits, parameters, and the absence of a hardware claim. |
| 03:20 | Training | If the environment has the optional quantum packages, run a bounded VQC, QSVC, or QNN configuration under the same comparison conditions. |
| 03:55 | Comparison | Show held-out metrics, validation summaries, timing, configuration, and neutral comparison language. Do not call a quantum model a winner without measured evidence. |
| 04:30 | Explainability | Request permutation, SHAP, or perturbation explanation as supported by the selected model and show the limitation text. |
| 05:00 | Research Prediction | Use one public demo sample or an authorized research input. Point out that the output is not a diagnosis. |
| 05:25 | Experiments | Open the experiment record, provenance, split fingerprint, job state, models, and report export. |
| 05:50 | Demo Center | Close with impact and future progression: larger cohorts, external validation, privacy-preserving collaboration, and future hardware evaluation remain research work—not current claims. |

## Reset checklist

- Start exactly one backend worker.
- Confirm `/api/health` is reachable.
- Load the demo dataset.
- Validate quality before training.
- Use a bounded configuration appropriate for the machine.
- Keep the research disclaimer visible.
- Do not pre-seed or fabricate experiment output.
