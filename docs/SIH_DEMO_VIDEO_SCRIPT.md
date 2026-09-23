# EntangleX Q-Health — SIH demo video script

**Target duration:** 3–5 minutes  
**Recording status:** Recording workflow prepared; no video file is claimed here.  
**Rule:** Record only values returned by the live backend. Never add a metric, readiness state, or quantum capability that the run did not produce.

## Pre-recording checklist

1. Start the FastAPI service and frontend using the commands in `README.md`.
2. Open **SIH Demo Center** and confirm the backend indicator is connected.
3. Register the bundled public Breast Cancer Wisconsin Diagnostic benchmark from **Datasets**.
4. Run validation, then a bounded classical experiment from **Training**.
5. Wait for the job to reach `SUCCEEDED` before recording comparison, explanation, prediction, or report screens.
6. If quantum packages are unavailable, show the explicit `UNAVAILABLE` / local-simulation boundary in Quantum Lab. Do not substitute a fictional circuit or result.
7. Clear any uploaded data or local runtime artifacts that are not part of the public demo before recording.

## Recording sequence

| Time | Screen and exact action | Suggested narration | Visual focus |
|---|---|---|---|
| 00:00–00:20 | **SIH Demo Center** → select Problem | “Biomedical ML research needs traceable data, controlled evaluation, and interpretable outputs—not a single unsupported score.” | Current-step spotlight and scientific guardrails |
| 00:20–00:45 | **Overview** → scroll through the workflow | “EntangleX Q-Health connects dataset provenance, quality checks, leakage-safe preprocessing, classical and quantum model paths, comparison, explainability, and experiment reports.” | Interactive research pipeline |
| 00:45–01:10 | **Datasets** → open the registered benchmark | “The dataset card exposes the source, target, class mapping, row and feature counts, and content hash before modeling.” | Provenance panel and quality state |
| 01:10–01:30 | **Data quality** → run validation | “Validation reports missingness, duplicates, class balance, identifier-like fields, and blockers. These are data-quality diagnostics, not clinical validation.” | PASS / WARNING / BLOCKED evidence |
| 01:30–01:55 | **Preprocessing**, **Features**, **PCA** → request previews | “Transformations are configured as part of the research pipeline. Training-only selection and PCA are inspected before a model sees the data.” | Stage configuration, measured scores, explained variance |
| 01:55–02:25 | **Training** → show model families and shared evaluation contract | “Classical baselines and quantum estimators use the backend’s configured representation and evaluation contract. The job state is live, not simulated in the UI.” | Model selector, seed, split, CV folds, job state |
| 02:25–02:50 | **Quantum Lab** → show capability, then Generate or Retrieve circuit when available | “The quantum page separates an accessible explanation from technical circuit metadata. Local simulation is reported explicitly; circuit depth and gate count are not presented as proof of advantage.” | Explain/Technical mode and circuit viewer |
| 02:50–03:20 | **Comparison** → choose the completed experiment | “Comparison keeps the same experiment conditions visible and reports measured accuracy, precision, recall, specificity, F1, ROC-AUC, timing, and limitations.” | Metric matrix, ROC view, shared conditions |
| 03:20–03:45 | **Explainability** → select a ready model and run a bounded method | “Feature influence describes model sensitivity for this run. It is not biological causation.” | Influence ranking, method, scope, limitations |
| 03:45–04:10 | **Research prediction** → load the public demo sample and submit | “This is a research prediction from an exact model schema. The output is not a diagnosis and the thresholds are not clinically validated cutoffs.” | Input schema, output semantics, disclaimer |
| 04:10–04:35 | **Experiment detail** → show lineage and export controls | “The run preserves dataset provenance, configuration, job history, model records, evaluation, explanation, and report export.” | Lineage, jobs, reports |
| 04:35–04:50 | Return to **SIH Demo Center** → next/previous controls | “The Demo Center keeps the presentation sequence anchored to live readiness, so an unavailable dependency is visible rather than hidden.” | Readiness states and navigation |

## Fallback paths

- **Backend unavailable:** show the clear offline state and stop before presenting metrics. Explain that the product is a live research workflow.
- **No registered dataset:** use `Datasets → Load benchmark`; do not claim a dataset is ready until registration succeeds.
- **Training takes too long:** use the bounded sample configuration already shown in the Training page. Wait for the real job, or end at the live job state and state that results were not computed in this run.
- **No completed experiment:** present the configuration and pipeline previews only. Label comparison, explanation, prediction, and reports `NOT YET RUN`.
- **Quantum dependency missing:** show `Quantum execution unavailable in this environment` / `UNAVAILABLE`. Do not fabricate a circuit, hardware result, or advantage claim.
- **Prediction sample unavailable:** use an authorized research input matching the displayed schema. Never upload patient-identifiable data.

## Reset instructions

1. Return to **SIH Demo Center** and verify live readiness.
2. Use the existing dataset registry controls to remove a temporary uploaded dataset if one was created.
3. Keep the public benchmark registration only if it is intended for the recording.
4. Do not commit `data/`, `models/`, `experiments/`, SQLite files, logs, or uploaded CSVs.
5. Restart the backend if a previous job is still active; confirm the job state before another recording attempt.

## Claims to avoid

- Do not say “quantum advantage,” “quantum superiority,” or “quantum wins.”
- Do not say “diagnoses,” “clinically validated,” “medical accuracy,” or “predicts disease in patients.”
- Do say “research prediction,” “benchmark classification,” “controlled comparison,” “local simulation,” “measured result,” and “feature influence.”
