# Scientific Audit Timeline & Immutable Event History

## 1. Purpose and Scientific Meaning

The **Scientific Audit Timeline** provides a first-class, immutable, and chronological record of meaningful research-platform events for EntangleX Q-Health.

It answers the foundational auditing question:
> **"What happened, when did it happen, what object changed or was created, what operation caused it, and what persisted state resulted?"**

The audit system records facts about **actions taken** and **resulting states persisted**. It intentionally avoids generating subjective claims:
- **Recorded fact**: *"Pipeline Version `v4` was published at time T."*
- **Excluded non-fact**: *"Pipeline Version `v4` is scientifically superior."*

---

## 2. Scientific Audit Timeline vs. Deep Experiment Lineage

The platform maintains a clear architectural distinction between Provenance and Audit:

| Dimension | Deep Experiment Lineage (Prompt 13) | Scientific Audit Timeline (Prompt 17) |
| :--- | :--- | :--- |
| **Question Answered** | *"Where did this research object come from?"* | *"What happened to this object over time?"* |
| **Data Structure** | Directed Acyclic Graph (DAG) of derivation and input-output nodes | Append-only chronological timeline of state transitions and events |
| **Focus** | Ancestry, dependencies, artifact parentage | Timestamped platform actions, executions, publications, checkpoints |
| **Relationship** | Can be referenced by audit events | Captures the act of lineage establishment without replacing lineage |

---

## 3. Immutability and Append-Only Integrity

Audit history is strictly append-only:
1. **ORM Layer Enforcement**: SQLAlchemy `before_update` and `before_delete` listeners intercept any attempt to mutate or delete existing `ScientificAuditEvent` records, raising an immutable violation exception.
2. **Deterministic Cryptographic Fingerprinting**: Every event generates a canonical SHA-256 fingerprint computed across its normalized fields (normalized to UTC, key-sorted JSON).
3. **Cryptographic Chaining**: Events targeting an object maintain a `previous_event_fingerprint` link pointing to the prior event, establishing a tamper-evident audit log.
4. **Integrity Verification Service**: The `/api/audit/integrity` endpoint scans events, verifies that stored fingerprints match recalculated SHA-256 hashes, validates category and event type vocabularies, and verifies chain continuity.

---

## 4. Persisted Data Model

The `scientific_audit_events` table is created via migration `20261003_14_scientific_audit_timeline`:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | String (UUID) | Unique primary key of the audit event. |
| `schema_version` | String | Fixed version (`scientific_audit_event_v1`). |
| `event_type` | String | Controlled event type (e.g. `EXPERIMENT_CREATED`). |
| `event_category` | String | Controlled category (e.g. `EXPERIMENT`, `RUN`). |
| `occurred_at` | DateTime (UTC) | When the action physically occurred. |
| `recorded_at` | DateTime (UTC) | When the event was committed to storage. |
| `actor_type` | String | Categorical actor (`system`, `user`, `worker`, `migration`, `api`). |
| `actor_reference` | String (Nullable) | Safe identifier of the initiating actor (e.g. user ID). |
| `source_component` | String | Backend subsystem (e.g. `backend.runs.service`). |
| `operation_key` | String (Nullable) | Unique key for deduplication and idempotent replay. |
| `object_type` | String | Target object type (`experiment`, `pipeline_version`, etc.). |
| `object_id` | String | Identifier of the target object. |
| `parent_object_type` | String (Nullable) | Optional parent entity type. |
| `parent_object_id` | String (Nullable) | Optional parent entity ID. |
| `before_fingerprint` | String (Nullable) | State fingerprint prior to the event. |
| `after_fingerprint` | String (Nullable) | Resulting state fingerprint after the event. |
| `previous_event_fingerprint` | String (Nullable) | Cryptographic pointer to previous event in sequence. |
| `event_fingerprint` | String | Deterministic SHA-256 hash of this event. |
| `metadata` | JSON | Structured contextual dictionary (sanitized). |

Unique index constraint: `uq_audit_operation_event` on `(operation_key, event_type)` ensures strict idempotency.

---

## 5. Controlled Event Taxonomy

Events are categorized under 11 controlled categories:

```text
EXPERIMENT  DATASET  PIPELINE  PROTOCOL  RUN
JOB         MODEL    EVIDENCE  ARTIFACT  CONFIGURATION
DEPLOYMENT
```

Supported event types include:
- **EXPERIMENT**: `EXPERIMENT_CREATED`, `EXPERIMENT_UPDATED`, `EXPERIMENT_COMPLETED`, `EXPERIMENT_FAILED`, `EXPERIMENT_CANCELLED`, `EXPERIMENT_ARCHIVED`
- **DATASET**: `DATASET_REGISTERED`, `DATASET_INSPECTED`, `DATASET_VALIDATED`, `DATASET_VERSION_CREATED`
- **PIPELINE**: `PIPELINE_CREATED`, `PIPELINE_VERSION_CREATED`, `PIPELINE_VERSION_PUBLISHED`, `PIPELINE_VERSION_DEPRECATED`
- **RUN**: `RUN_CREATED`, `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `RUN_CANCELLED`
- **JOB**: `JOB_CREATED`, `JOB_STARTED`, `JOB_PAUSED`, `JOB_RESUMED`, `JOB_COMPLETED`, `JOB_FAILED`, `JOB_CANCELLED`, `CHECKPOINT_CREATED`
- **MODEL**: `MODEL_REGISTERED`, `MODEL_METRICS_RECORDED`, `MODEL_CARD_GENERATED`
- **EVIDENCE**: `EVIDENCE_PACKAGE_CREATED`, `CONTROLLED_COMPARISON_CREATED`, `CALIBRATION_EVALUATED`, `THRESHOLD_ANALYZED`, `ROBUSTNESS_EVALUATED`
- **ARTIFACT**: `ARTIFACT_REGISTERED`, `ARTIFACT_VERIFIED`

---

## 6. Privacy & Data Minimization

The audit engine enforces strict data sanitization rules:
- **No Protected Health Information (PHI)** or patient-level record rows are ever logged.
- **No Credentials**: API tokens, authorization headers, passwords, and secrets are stripped recursively from event metadata.
- **Bounded Payloads**: Large raw lists and deep dictionaries are truncated to summarize count and keys.

---

## 7. Integrated Subsystems

Scientific audit events are recorded across all major platform components:
1. **Runs Service**: Emits `RUN_CREATED`, `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `RUN_CANCELLED`.
2. **Artifacts & Model Registry**: Emits `ARTIFACT_REGISTERED` and `MODEL_REGISTERED` with artifact hashes.
3. **Research Evidence Packages**: Emits `EVIDENCE_PACKAGE_CREATED` capturing package fingerprints.
4. **Pipeline Version Registry**: Emits `PIPELINE_VERSION_CREATED` and `PIPELINE_VERSION_PUBLISHED`.
5. **Resumable Jobs Engine & Manager**: Emits `CHECKPOINT_CREATED`, `JOB_STARTED`, `JOB_PAUSED`, `JOB_RESUMED`, `JOB_COMPLETED`, and `EXPERIMENT_CREATED` / `EXPERIMENT_COMPLETED`.
6. **Experiment Reports**: Embeds the audit summary directly into exported HTML and JSON research reports.

---

## 8. REST API Endpoints

- `GET /api/audit/events`: Paginated, filterable event listing with deterministic ordering (`occurred_at DESC, id DESC`).
- `GET /api/audit/integrity`: Validates log integrity and cryptographic event hash chains.
- `GET /api/experiments/{id}/audit`: Returns the unified audit timeline for an experiment and its child runs/jobs/models, including integrity verification.
- `GET /api/experiments/{id}/audit/export`: Deterministic, machine-readable JSON download containing event history, hashes, and platform version.
- `GET /api/audit/{object_type}/{object_id}`: Returns the audit timeline for an arbitrary research object.

---

## 9. Scientific Boundaries and Limitations

1. **Non-Causal**: The audit timeline records timestamps and sequential platform operations; it does not infer causal relationships between pipeline configuration and outcomes.
2. **No Quality Evaluation**: Event history indicates that an operation occurred, not that the resulting model is clinically validated or accurate.
3. **Legacy Historical Notice**: Experiments executed prior to migration `20261003_14_scientific_audit_timeline` contain a transparent disclaimer noting that audit logging began with the platform upgrade. No historical events are fabricated.
