# Quantum pipeline

## Implementation target, not executed compatibility

The isolated adapter uses the verified set Qiskit 2.5.2, Qiskit Machine Learning 0.9.1 and Qiskit Aer 0.17.2. Source inspection of official APIs informed the code, and the selected Qiskit objects were constructible in the clean environment recorded in `verified_environment.md`. Sampler execution, training and serialization were **not** performed during generation or this dependency-stabilization task.

## Shared biomedical representation

All selected classical and quantum models receive the same outer dataset subset, split, selection configuration and PCA dimension. Quantum runs require PCA components equal to qubits and training-fitted angle scaling. The default is four qubits, one feature-map repetition, one ansatz repetition and a 30-iteration optimizer cap. The default 160-sample budget is an execution configuration, not a measured performance result. All comparable models share this budget.

## Estimators

`QuantumClassifier` exposes sklearn-compatible `fit`, `predict`, conditional `predict_proba`, `decision_function`, `classes_` and cloneable constructor parameters. It is constructed only when the requested model is VQC/QSVC; imports are lazy enough for the classical-only installation.

VQC uses functional `zz_feature_map` and `real_amplitudes` builders, seeded initial weights, a configurable COBYLA or SPSA optimizer, and a SamplerV2-compatible primitive. Objective callback values are recorded only as actually produced by optimization. They are optimizer objectives, not accuracy or clinical validation curves.

QSVC uses `FidelityQuantumKernel` with `ComputeUncompute` and the configured sampler. Its SVC probability mode is disabled. QSVC decisions are margins with a zero cutoff and do not receive probability-based risk categories. The circuit screen displays the feature map; actual kernel computations use compute-uncompute circuit pairs. Logical depth shown by the screen is not a transpiled hardware timing estimate.

## Backend abstraction

`QuantumBackend` provides sampler, optional pass manager and execution metadata. `StatevectorBackend` uses QMLSampler with `shots=None`, for analytic local statevector evaluation. `AerBackend` uses Aer `SamplerV2` with explicit shots and a transpilation pass manager for its basis gates. Aer can apply illustrative one- and two-qubit depolarizing noise. A noise probability above zero is rejected for the analytic statevector backend.

Finite shots introduce sampling variability; seeds do not establish numerical identity across dependency versions/platforms. The noise model is a research mechanism, not calibrated hardware characterization. Package presence detection reports availability only, never successful simulation.

## Circuit retrieval

`POST /api/quantum/circuit` builds a parameterized circuit at request time and calculates qubit count, logical depth, operations, parameters, display instructions and text drawing. It does not execute the circuit. `GET /api/models/{id}/circuit` retrieves the stored trained-model circuit specification. The frontend renders computed instructions with a bounded view and includes full textual output.

## Training and cost boundaries

Every CV fold trains a fresh quantum estimator and fitted preprocessing pipeline. Final fit is separate. The bounded single-worker queue prevents multiple simultaneous training jobs in this process. Optimizer caps and sample caps are safety limits, not training-time promises. Cancellation is checked between phases; it cannot interrupt a simulator/optimizer call instantly.

No fallback fabricates a quantum prediction. Missing packages, invalid shapes or API incompatibilities produce explicit unavailable/failed states. A failed model remains visible alongside successful classical baselines. Dill persistence of Qiskit objects is implemented but unverified across versions; only reload in the locally validated matching environment.

## Scientific claims

Quantum simulation runs on classical hardware. Real hardware execution is not implemented. Comparing prediction quality and measured local computation is legitimate, but this MVP does not establish asymptotic speedup, general quantum advantage, clinical validity or statistically significant superiority. A classical win, a sensitivity-specificity tradeoff, higher quantum cost or no measurable benefit are all valid reported outcomes.
