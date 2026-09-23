# EntangleX Q-Health — SIH Technical Summary

## Problem

Biomedical disease-risk research requires traceable data, explicit positive-class semantics,
leakage-safe preprocessing, interpretable outputs, and fair evaluation of multiple model
families. A single performance number is not enough to reproduce or explain a research result.

## Solution

EntangleX Q-Health is a local research platform for registering benchmark or deidentified CSV
datasets, validating data quality, configuring a shared preprocessing pipeline, training
classical and hybrid quantum-classical estimators, comparing them under equivalent conditions,
requesting bounded explanations, making research-only predictions, and preserving experiment
provenance.

## Architecture

```text
React 19 + TypeScript + Vite
             │ same-origin /api
FastAPI + Pydantic schemas + safe error handling
             │ services / repositories
SQLite dataset, experiment, model, explanation and job registries
             │ bounded single-worker training
scikit-learn pipelines + optional Qiskit/Qiskit ML/Aer
             │ trusted local artifacts and hashes
held-out metrics + reports + research prediction
```

## Frontend

The interface is a responsive research workspace with grouped navigation, live system status,
an inspector, keyboard command palette, presentation rail, settings center, data tables, charts,
quantum circuit views, model detail surfaces, and explicit empty/loading/error states. The SIH
Demo Center guides a judge through the real screens rather than a disconnected slideshow.

## Backend and ML

The backend supports:

- CSV upload and public benchmark registration with provenance and SHA-256 hashing;
- aggregate data-quality checks for missingness, duplicates, class balance, suspicious proxies,
  identifier-like columns, and correlations;
- training-only imputation, scaling, clipping, ratios, log transforms, selection, PCA, and
  optional angle scaling;
- Logistic Regression, SVM, Random Forest, VQC, QSVC, and QNN model identifiers under the
  existing registry/training architecture;
- held-out metrics, CV summaries, ROC information, timing, confusion counts, and failures;
- model persistence with artifact hashes, prediction schema validation, reports, and reruns.

## Quantum and QNN

Quantum estimators use local simulation through the existing quantum adapter. QNN support is
provided through the existing Qiskit Machine Learning path when optional dependencies are
installed. The UI and API distinguish exact statevector simulation, finite-shot Aer simulation,
and real hardware; real hardware credentials and execution are not implied.

## Evaluation and explainability

Models in one experiment share dataset provenance, raw feature schema, split, preprocessing
configuration, and comparison conditions. Metrics remain null when undefined. Explanations use
permutation, SHAP, or perturbation methods as supported by the model and disclose their scope,
sample budget, elapsed time, and limitations. Feature influence is not biological causation.

## Security and reproducibility

The API supports optional bearer authorization, trusted hosts, origin checks, bounded request
bodies, sanitized errors, no-store responses, safe upload paths, generated storage identities,
artifact integrity checks, and no raw biomedical payload logging. UI tokens are held in memory.
Experiment records retain configuration, split fingerprints, source hashes, software versions,
model status, and limitations.

## Limitations, scalability, and future work

This is a single-user, single-worker local research prototype. It is not a clinical product,
regulated deployment, de-identification guarantee, public multi-tenant service, or proof of
quantum advantage. Future work includes external validation cohorts, grouped/time-series
validation, privacy-preserving collaboration, stronger deployment isolation, distributed job
execution, broader datasets, and measured hardware experiments when appropriate.