# Research evaluation source contexts

EntangleX research evidence is resolved from one of two authoritative contexts.

## Live run

`source_context_type = "live_run"` means the `ModelRecord` is linked to a persisted
`Run`. The Run supplies the locked training configuration, experiment and dataset
lineage, dataset version, manifest references, and reproducibility metadata.
Existing live-run behavior is preserved.

## Verified demo experiment

`source_context_type = "verified_demo_experiment"` means the model belongs to the
immutable, precomputed verified-demo package. These models intentionally may not
have a `Run`, because the package was not produced by a live training execution in
the current registry. The authoritative context is the verified `Experiment`
configuration plus the verified `Dataset`, `ModelRecord`, artifact hash, package
manifest, and dataset provenance. No substitute Run is created.

The shared evaluation-context resolver verifies that the model, experiment,
dataset, optional dataset version, and packaged artifact identity belong together
before an analysis runs.

## Feature behavior

- **Calibration Laboratory** prepares evaluation data from the resolved locked
  configuration and persists the source context with computed metrics and the
  reliability curve. Current scientific policy limits calibration to supported
  classical models.
- **Threshold Analysis** uses the same context. It sweeps and selects a threshold
  on a dedicated selection subset, freezes it, and evaluates it on a separate
  evaluation subset. Provenance records both populations and the selection method.
- **Quantum Research Diagnostics** derives configuration facts from the resolved
  experiment and model provenance. It does not invent runtime, loss-history,
  hardware, noise, or quantum-advantage evidence.
- **Model Cards** are deterministic views of persisted evidence. Missing optional
  studies are represented as `not_available` with explicit evidence gaps; they do
  not make the card endpoint fail. Completed compatible studies automatically
  change the relevant evidence status to `available`.

These capabilities are research-evaluation tools only. They do not establish
clinical validity, deployment readiness, prospective population performance, real
quantum-hardware execution, or quantum advantage.