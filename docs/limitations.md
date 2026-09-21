# Known limitations and non-claims

## Generation and verification

During source generation, the application was not executed. That historical statement remains true for the generation task. Post-generation Task 1 verification established clean dependency resolution, Python imports, backend startup/API workflows, TypeScript type checking, frontend tests/build/runtime, API integration, classical and bounded quantum execution, security/storage behavior, and the complete native regression. Docker build/runtime remains unverified because the Docker CLI/daemon was unavailable in the final closure environment. Static syntax/presence checks are documented separately and must not be described as application tests. See `docs/task1_final_verification.md`.

## Biomedical validity

This is research software, not a clinically validated diagnostic device. The public WDBC example classifies benchmark labels and does not establish prospective early detection, clinical utility, regulatory approval, patient safety, treatment efficacy, prognosis or real-world diagnostic performance. Strong benchmark scores are insufficient evidence for any of these claims.

Only independent-sample binary tabular classification is implemented. Grouped subjects, repeated visits, temporal prediction, survival analysis, multi-label/multiclass tasks, raw ECG/imaging/genomic processing, external-cohort validation and validated subgroup analysis are not implemented. Imaging-derived or genomic-derived tabular features can be inputs only when the independent binary-task assumptions are actually appropriate.

There are no clinical normal ranges, disease-specific clinical rules, medically validated risk thresholds or treatment advice. Positive labels come from metadata, not disease-name branches. Research probability bins are presentation aids, not clinical recommendations.

## Statistical and methodological limits

The default benchmark is a small seeded subset so a quantum demonstration is tractable. It is not representative of a deployed clinical population. All models share the same subset, but one seed and CV dispersion do not establish significance, robustness or general quantum advantage. Hyperparameter search is intentionally absent; configured settings are evaluated rather than tuned on the holdout. Repeated reruns/holdout inspection can still bias human selection.

No bootstrap confidence intervals or external validation are bundled. Calibration is classical-only and internally cross-validated; it is not clinically validated. SVM/QSVC margins are not probabilities. ANOVA and mutual-information selection use their library assumptions, and encoded categorical MI is treated with the selector's dense-feature convention. Investigate feature-type assumptions before scientific publication.

Whole-source quality checks are descriptive and include heuristic target-proxy screening. They are not a clinical or causal data validation engine. Identifier heuristics are incomplete. Conservative duplicate rejection may flag legitimate repeated vectors; group-aware validation is needed rather than bypassing the safety check for dependent observations.

## Quantum and explainability limits

All quantum execution is local simulation. Four-qubit/lightweight defaults are engineering budgets, not scientific evidence. Finite shots, optimization caps and unverified version-sensitive APIs can affect outcomes. Noise simulation is illustrative, not calibrated physical hardware. There is no hardware-provider authentication, mitigation study, quantum speedup proof or quantum-specific probability calibration.

Quantum object serialization/reloading with dill was verified for the targeted package combination on the bounded VQC/QSVC artifacts. This does not guarantee compatibility across arbitrary future package versions. Classical/quantum comparison uses identical feature pipelines but does not guarantee matched hyperparameter optimization effort or controlled compute resources.

SHAP supports complete numeric raw inputs in this implementation. Permutation importance needs both classes in its bounded explanation subset. Perturbation covers a disclosed limited feature count, may be off-manifold, and does not completely interpret circuit internals. Feature influence is not biological causation. Model prediction inputs are not persisted; a user must deliberately retain approved inputs outside this service for a separate audit workflow.

## Operational and security limits

The worker is in-process, single-process and cooperatively cancellable between fit phases, not instantaneously interruptible. It is not a durable distributed queue. Restart marks active work interrupted instead of claiming resume. There is no guaranteed hard runtime/memory limit per model beyond declared configuration and queue bounds.

Storage is SQLite plus local files. Initial schema creation is provided, not a future migration framework. The UI shows the first 100 registry records; API endpoints support pagination. HTML/JSON reports are implemented; PDF export is not included. Explanation requests are synchronous and bounded; a long quantum explanation can hold a request open.

The local token is not account management, RBAC, tenant separation or compliance certification. There is no automatic de-identification, managed encryption, TLS service, automated retention, full medical audit trail or public-deployment hardening. Protect uploaded data, serialized models and registry hashes together.

## Exact medical disclaimer

> **Research Prototype:** This platform provides model-generated disease-risk predictions for research and decision-support purposes. Predictions are based on benchmark or user-provided datasets and are not a substitute for professional medical diagnosis, treatment, or clinical validation.
