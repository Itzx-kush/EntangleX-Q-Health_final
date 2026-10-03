# Experiment Protocols & Reusable Research Templates

## Purpose

The Experiment Protocol and Reusable Research Template system allows researchers to define standardized, explicit experimental specifications before conducting experiments and preserves the exact immutable protocol version that was applied when each result was produced.

The system answers:

> **“What experimental rules were defined before this experiment, and exactly which protocol version was applied when the result was produced?”**

## Core Scientific Principle

A protocol is an **explicit experimental specification**. It defines how an experiment is intended to be conducted, bounded, and evaluated.

It specifies rules such as:

- task type and study scope
- dataset selection requirements and target definition
- train/validation/test split and cross-validation strategy
- seed policy and determinism requirements
- evaluation metrics and primary metric designation
- decision threshold selection and locking policy
- calibration requirements
- external validation and distribution-shift extensions
- classical-vs-quantum comparison controls

### What a Protocol Does Not Do

A protocol does **not** establish that an experiment was successful, valid, or clinically deployable.

- **Correct:** *Experiment EXP-42 followed Protocol v2.*
- **Incorrect:** *Protocol v2 proves the model is reliable or clinically ready.*

## Protocols vs Pipelines vs Evidence vs Lineage

To maintain strict scientific and architectural boundaries:

| System | Role | What It Contains |
|---|---|---|
| **Experiment Protocol** (Prompt 15) | Experimental Rules | What *should* happen: task, dataset requirements, split policy, seed count, required metrics, threshold lock, calibration requirements. |
| **Pipeline Version Registry** (Prompt 14) | Computational Steps | How computation is executed: ordered transformations, scalers, encoders, model architecture, quantum circuit configuration. |
| **Deep Experiment Lineage** (Prompt 13) | Graph Traceability | How artifacts are connected: directed provenance edges between datasets, pipelines, experiments, runs, models, and packages. |
| **Research Evidence Packages** (Prompt 12) | Measured Evidence | What *actually* happened: verified metrics, ROC curves, calibration curves, confusion matrices, audit logs, and hardware execution manifests. |

## Data Model & Architecture

The system provides three first-class persisted entities:

1. **`ProtocolTemplate`** (`protocol_templates`):
   - Reusable experimental specifications that researchers can inspect and instantiate across multiple experiments.
   - Seeded with 5 built-in biomedical research templates.
   - Contains `template_id`, `name`, `description`, `task_type`, `canonical_definition`, `parameters_schema`, and `template_fingerprint`.

2. **`ExperimentProtocol`** (`experiment_protocols`):
   - A named protocol family (e.g., `Biomedical Classification Protocol Family`).
   - Groups successive immutable versions over time.

3. **`ExperimentProtocolVersion`** (`experiment_protocol_versions`):
   - The exact, immutable protocol definition applied to experiments.
   - Contains `protocol_version_id`, `protocol_id`, `version`, `version_number`, `schema_version`, `status`, `definition_fingerprint`, references to pipeline versions or controlled comparison protocols, and the canonical JSON definition.
   - Referenced by `Experiment.protocol_version_id` and `Run.protocol_version_id`.

## Canonical Protocol Schema

Every protocol version adheres to the `experiment_protocol_v1` schema:

- **`study`**: task type (`binary_classification`, `multi_class`, `regression`), study purpose, scope.
- **`dataset`**: selection strategy, required target column, label semantics.
- **`split`**: strategy (`train_test_split`, `stratified_kfold`, `group_kfold`, etc.), test ratio, cv folds, grouping columns.
- **`randomness`**: seed policy (`single_fixed_seed`, `fixed_seed_list`, `multi_seed`), primary seed, seed list, multi-seed count.
- **`model`**: model class reference, configuration requirements.
- **`pipeline`**: reference to `pipeline_version_id` or pipeline fingerprint.
- **`evaluation`**: primary metric, secondary metrics, aggregation methods, confidence intervals.
- **`threshold`**: selection method (`fixed`, `youden_index`, `f1_optimal`, `cost_optimal`), evaluation threshold, lock flag.
- **`calibration`**: requirement policy, method (`isotonic`, `platt`, `temperature_scaling`), split.
- **`validation_extensions`**: external validation, multi-seed count, distribution shift, robustness checks.
- **`quantum_controls`**: controlled comparison requirement, sample parity, preprocessing parity, seed parity.
- **`constraints`**: structured machine-readable validation rules (e.g., `minimum_seed_count`, `required_cv_folds`).

## Requirement Policies: Required vs Optional vs Disabled

Protocol sections explicitly declare requirement policies:

- **`REQUIRED`**: Mandatory for protocol compliance. If missing or mismatched in the experiment, recorded as `MISSING` or `MISMATCHED`.
- **`OPTIONAL`**: Permitted extension (e.g., external validation or robustness scan). If omitted by the experiment, recorded as `NOT_APPLICABLE` rather than a failure.
- **`DISABLED`**: Explicitly prohibited under this protocol (e.g., quantum advantage claims without classical controls).

## Rules, Not Results

A protocol describes what experimental conditions should occur, never experiment outcomes:

- **Allowed in Protocol**: `primary_metric: "roc_auc"`, `required_target_column: "diagnosis"`, `cv_folds: 5`.
- **Prohibited in Protocol**: `roc_auc: 0.94`, `accuracy: 0.91`, `p_value: 0.002`.

Outcomes belong strictly to runs, models, and evidence packages.

## Deterministic Protocol Fingerprint

`definition_fingerprint` is a SHA-256 hash computed over the normalized, canonical protocol definition.

- Canonicalization recursively sorts dictionary keys, standardizes floating-point representations, strips volatile fields (timestamps, IDs, database sequence numbers), and enforces UTF-8 encoding.
- Two identical protocol definitions always produce the exact same fingerprint.
- Any change to experimental rules produces a different fingerprint.

## Protocol Lifecycle & Immutability

Supported lifecycle states:

- **`DRAFT`**: Editable specification under design.
- **`PUBLISHED`**: Canonicalized, fingerprinted, and frozen. Cannot be edited.
- **`DEPRECATED`**: Superseded by a newer protocol version. Historical experiments continue pointing to it.
- **`ARCHIVED`**: Preserved for historical provenance only.

### Immutability Invariant

Once a protocol version is `PUBLISHED` or referenced by any `Experiment` or `Run`, it cannot be altered. Database event listeners reject any update or deletion. Changes require creating a new protocol version with an incremented version number and optional `parent_protocol_version_id`.

## Factual Protocol Compliance Verification

When evaluating an experiment against its attached protocol (`GET /api/experiments/{id}/protocol/compliance`):

- The engine performs structured checks comparing expected protocol rules against actual recorded experiment metadata, dataset targets, split folds, seeds, and evidence.
- Each check yields one of five factual statuses:
  1. **`MATCHED`**: Recorded experiment configuration or artifact strictly meets the protocol specification.
  2. **`MISSING`**: A `REQUIRED` item was not recorded in the experiment.
  3. **`MISMATCHED`**: An experiment setting contradicts the protocol (e.g., protocol required 5 folds, but experiment executed 3).
  4. **`NOT_APPLICABLE`**: An `OPTIONAL` item was not executed.
  5. **`UNVERIFIABLE`**: The evidence needed to confirm the rule cannot be resolved from persisted records.

### Anti-Scoring Guarantee

Compliance reporting **never** computes a percentage score, letter grade, pass/fail composite, or quality index. Missing evidence is never automatically executed.

## Built-In Research Templates

The system ships with 5 standard templates:

1. **`tpl-biomed-classification`**: Biomedical Binary Classification (5-fold stratified CV, multi-seed list, ROC-AUC + PR-AUC, Youden threshold lock, required calibration).
2. **`tpl-external-validation`**: External Validation Study (frozen primary benchmark, held-out external validation dataset required, distribution shift scan).
3. **`tpl-quantum-controlled`**: Quantum-vs-Classical Controlled Study (dataset parity, preprocessing parity, identical seed list, classical baseline mandatory).
4. **`tpl-multiseed-eval`**: Multi-Seed Evaluation Study (minimum 5 independent seeds, metric variance aggregation, determinism required).
5. **`tpl-robustness-eval`**: Robustness & Distribution Shift Study (synthetic noise scenarios, missing-value stress testing, subgroup shift verification).

## Structured Version Diffing

`GET /api/protocols/{id}/diff/{other_id}` produces a structured difference between two protocol versions:

- Reports additions, removals, and changes across categories (`study`, `dataset`, `split`, `randomness`, `evaluation`, `threshold`, `calibration`, `quantum_controls`).
- Summarizes category-level modifications (`Changed`, `Unchanged`).
- Provides neutral interpretation text. Does not rank or claim one version is superior to another.

## Lineage & System Integration

- **Execution Manifests**: Run manifests record `protocol_version_id` and `protocol_fingerprint`.
- **Experiment Reports**: HTML and JSON reports display protocol version, fingerprint, and compliance status.
- **Lineage Service**: Graph represents:
  - `ExperimentProtocol` → `has_version` → `ExperimentProtocolVersion`
  - `ProtocolTemplate` → `instantiated_as` → `ExperimentProtocolVersion`
  - `ExperimentProtocolVersion` → `applied_to` → `Experiment`
  - `ExperimentProtocolVersion` → `uses_pipeline` → `PipelineVersion`
  - `ExperimentProtocolVersion` → `derived_from` → parent `ExperimentProtocolVersion`
- **Research Evidence Packages**: Packages include `protocol_version_id` and `protocol_fingerprint` in their manifest and cryptographic fingerprint basis.
- **Model Cards**: Model cards disclose the protocol version under their reproducibility and provenance sections.
- **Legacy Compatibility**: Experiments run before Protocol Registry integration return `LEGACY_UNSPECIFIED`. No historical protocol is fabricated.

## REST API Reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/protocols` | `GET` | List all protocol versions with usage counts. |
| `/api/protocols` | `POST` | Create a new protocol version draft. |
| `/api/protocols/preflight` | `POST` | Preflight validate a protocol definition. |
| `/api/protocols/{id}` | `GET` | Inspect a specific protocol version. |
| `/api/protocols/{id}/publish` | `POST` | Validate, freeze, and publish a draft protocol version. |
| `/api/protocols/{id}/diff/{other_id}` | `GET` | Compute structured diff between two protocol versions. |
| `/api/protocol-templates` | `GET` | List available reusable research templates. |
| `/api/protocol-templates/{id}` | `GET` | Inspect a research template. |
| `/api/protocol-templates/{id}/instantiate` | `POST` | Instantiate a template into a new protocol version. |
| `/api/experiments/{id}/protocol` | `GET` | Get protocol attached to an experiment (or `LEGACY_UNSPECIFIED`). |
| `/api/experiments/{id}/protocol/attach` | `POST` | Attach a published protocol version to an experiment. |
| `/api/experiments/{id}/protocol/compliance` | `GET` | Evaluate factual protocol compliance against experiment evidence. |

## Privacy & Security

Protocol definitions describe experimental methodology only. They never store:

- patient records or raw clinical data
- CSV rows or patient health identifiers (PHI)
- credentials, API keys, passwords, or tokens
- internal file system paths

Preflight validation strictly rejects prohibited fields and credentials.
