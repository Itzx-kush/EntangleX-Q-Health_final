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

## Quantum/classical evidence records

For each completed quantum/classical pair in one experiment, comparison now
returns a structured evidence object while preserving the original delta
fields. It contains actual held-out performance values and signed deltas,
measured final-training/CV/inference timings, recorded quantum backend and
logical circuit resources, shared dataset/split/preprocessing context, each
model's research operating point, and a neutral descriptive conclusion.

Logical depth, gates, qubits, shots, and parameter counts are reported as
logical resources and simulator settings, not converted into hardware runtime
or financial cost. Missing legacy metadata remains absent. Unfavorable quantum
results remain visible. The evidence engine never emits a general quantum
advantage or clinical-validation conclusion.

## Adaptive resource and experiment-budget advisor

`POST /api/quantum/resource-advisor` performs a cheap, deterministic planning
check; it never builds or executes a quantum circuit. Policy
`bounded-simulator-resource-policy-v1` reads the authoritative Pydantic schema
bounds and runtime quantum sample cap, then applies one documented, stricter
single-workstation policy: at most 6 qubits, 2 feature-map repetitions, 2
ansatz repetitions, 100 requested optimizer iterations, 4096 Aer shots, and
the configured `quantum_max_samples` value. A dimension at or above 75% of a
policy limit is labelled near budget. These are engineering guardrails inside
the wider valid request schema, not hardware or model-quality limits.

The resource profile keeps circuit width/repetitions, optimizer iterations,
Aer shots, sample count, backend, entanglement, and noise mode separate.
Statevector execution reports shots as not applicable. Logical depth, gate
count, and parameter count remain null until an actual generated or fitted
circuit supplies them; they are never guessed.

For near/over-budget numeric dimensions, recommendations reduce pressure in
the fixed order shots, optimizer iterations, ansatz repetitions, feature-map
repetitions, qubits, and sample count. Targets come from the validated default
configuration and the configured sample cap. Every output includes the
original request, changed fields and reasons, before/after profiles, and policy
version. The backend validates the proposed quantum/PCA/sample combination
through `TrainingConfig`. Nothing changes until the user explicitly selects
**Apply recommended configuration**; applying only updates the existing draft
and does not launch training.

Observed history uses only ready records with the same model type, backend, and
qubit count, bounded to 20 matches ranked by matching request context and
configuration factors. Median/range values come only from recorded `final_training_seconds`; per-run CV, inference, objective,
circuit, and sample context remain visible. No wall-clock value is extrapolated
for a new request. Local simulator resource dimensions are not QPU performance,
and hardware execution remains unavailable in the verified configuration.

## SIH Judge Alignment — Executable Hybrid Model (2026-09-30)

The additive `hybrid_pennylane_torch` path uses the existing fitted sklearn preprocessing pipeline, then a PennyLane `default.qubit` QNode with Y-axis `AngleEmbedding`, trainable `StronglyEntanglingLayers`, and one Pauli-Z expectation output per qubit. A PyTorch CPU head consumes those expectations and trains jointly with the circuit using `BCEWithLogitsLoss` and Adam or SGD. Quantum parameters participate in backpropagation; fixed precomputed quantum features are not used.

Qiskit VQC/QSVC/QNN configuration remains separate. A shared experiment containing both families must use matching PCA and qubit dimensions. Circuit resources are derived from the instantiated PennyLane template where available; they are logical simulator metadata, not hardware cost. Real hardware and general quantum advantage remain unestablished.
