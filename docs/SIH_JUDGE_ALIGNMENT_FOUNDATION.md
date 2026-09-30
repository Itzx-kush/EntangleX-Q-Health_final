# SIH Judge Alignment — Foundation

**Date:** 2026-09-30

## Scope

The flagship presentation context is **Early Stage Diabetes Risk Prediction**, backed by the existing immutable `early-stage-diabetes` catalog entry and its recorded SHA-256. This is a featured demonstration, not the platform's only supported disease or dataset.

The prepared `hybrid_pennylane_torch` architecture is:

1. data validation;
2. classical preprocessing;
3. bounded feature selection/dimension reduction;
4. PennyLane quantum feature transformation and circuit;
5. expectation-value representation;
6. PyTorch classical output head;
7. positive-class probability;
8. the existing OOF-validated sensitivity-first threshold;
9. research-only risk stratification;
10. SHAP explanation over original input features through the complete predictor.

## Truthful capability boundary

Prompt 1 provides schemas, API metadata, UI presentation, dependency bounds, and tests only. Hybrid training, prediction, robustness, comparison evidence, and SHAP execution are `NOT_YET_IMPLEMENTED`. No placeholder estimator or fabricated output is used. Real quantum hardware is unavailable and no quantum advantage, clinical validation, diagnosis, or outcome claim is made.

Existing Qiskit, Qiskit Aer, VQC, QSVC, QNN, classical models, threshold optimization, evidence comparison, frozen-artifact robustness, explainability, resource advice, persistence, registries, reports, and responsive navigation remain supported. Prompt 2 may implement the bounded PennyLane/PyTorch estimator behind the prepared contracts without creating parallel threshold, comparison, or robustness engines.

## Dependency preparation

`backend/requirements-hybrid.txt` isolates `pennylane>=0.43,<0.44` and `torch>=2.7,<2.10` for explicit Prompt 2 installation in the repository's Python 3.11 environment. They are intentionally excluded from `requirements.txt` in Prompt 1 so deployment size and existing verified environments do not change before execution exists.

## SIH Judge Alignment — Executable Hybrid Model (2026-09-30)

Prompt 2 replaces the foundation-only boundary with a real sklearn-compatible `PennyLaneTorchClassifier`. It reconstructs runtime-only PennyLane/PyTorch objects from application-owned configuration and NumPy weight arrays during secure artifact reload, without broadening the restricted-unpickler allowlist. The model participates in the existing CV/OOF threshold loop and records actual circuit/head parameter counts, package versions, measured timing, simulator metadata, and limitations.

The first bounded end-to-end validation uses the existing Early Stage Diabetes catalog record and mixed categorical/numeric inputs. No CSV duplication or modification is performed. Qiskit models remain supported and separately configured. Real hardware, clinical validation, diagnostic use, cross-platform bit-for-bit determinism, speedup, superiority, and general quantum advantage are not claimed.
