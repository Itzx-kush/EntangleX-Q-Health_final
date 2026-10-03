# Scientific CI verification

**Scope:** implementation-level scientific, reproducibility, provenance, data-integrity and deployment
invariants. Scientific CI is a verification and CI-gating layer; it is not a research feature.

> Scientific CI verifies implementation-level scientific and reproducibility invariants.
> A passing CI run does **not** constitute independent scientific validation of any model, dataset,
> experiment, or biomedical conclusion.

## Purpose

Scientific CI answers factual questions about the repository before a change reaches `main`:

```text
Does the application import successfully?
Do backend tests pass?
Do frontend tests pass and does the production build succeed?
Do migrations apply and stay idempotent?
Are required scientific tables and columns consistent with the ORM?
Are immutable fingerprints deterministic?
Are published scientific records still immutable?
Are forbidden production imports absent?
Are scientific protocol invariants preserved?
Does the build remain deployable?
```

It deliberately does **not** answer:

```text
Is this model scientifically superior?
Is this experiment high quality?
Is this dataset clinically valid?
Is this result trustworthy?
Which model is best?
```

Those require scientific interpretation beyond CI, so no check produces a scientific "score".

## Ordinary CI versus Scientific CI

```text
                ┌──────────────────────┐
                │ Ordinary CI          │  tests / typecheck / build
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Scientific CI        │  reproducibility and integrity invariants
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Deployment gate      │
                └──────────────────────┘
```

Ordinary CI is not replaced; Scientific CI extends it. `.github/workflows/ci.yml` runs the ordinary
suite, and `.github/workflows/scientific-ci.yml` runs the Scientific CI gate.

## Local execution

```bash
cd backend
python -m app.verification --profile fast     # pull-request gate (exit 0 / 1 / 2)
python -m app.verification --profile full     # broader profile
python -m app.verification --list             # every registered check
python -m app.verification --check subgroup_contract   # one check (repeatable)
python -m app.verification --print-baseline   # scientific baseline document
```

The repository's ordinary commands remain unchanged:

```bash
cd backend
python -m pytest -m "not quantum"             # ordinary backend suite
python -m pytest -m quantum                   # opt-in quantum tests
cd ../frontend
npm ci
npm test
npm run build                                 # includes TypeScript checking
```

A developer can reproduce the exact CI failure locally by running the failing `--check` id.

## Architecture

```text
backend/app/verification/
  __main__.py       CLI entry point (`python -m app.verification`)
  models.py         result contract: status, severity, failure category
  registry.py       check registry, profiles, manifest
  service.py        execution engine, summary, exit codes
  isolation.py      throw-away storage root, no secrets, subprocess environment
  fixtures.py       deterministic synthetic fixtures (never real data)
  baseline.py       reviewed scientific baseline (schema versions, fingerprints, required checks)
  checks/           one module per verification area
```

Each check registers itself with the registry and returns a structured `CheckResult`:

```json
{
  "check_id": "pipeline_version_immutability",
  "category": "PIPELINE INTEGRITY",
  "status": "PASS",
  "severity": "REQUIRED",
  "message": "Published pipeline versions and their stages reject mutation and keep their fingerprint.",
  "evidence": {"pipeline_version_id": "...", "definition_fingerprint": "..."}
}
```

## Check registry

The registry in `backend/app/verification/registry.py` is the single source of truth. It is exported
three ways so it cannot drift:

* the CLI (`--list`, `--manifest-out`)
* `scientific-ci-manifest.json` (committed machine-readable list)
* `GET /api/system/scientific-ci` (read-only contract endpoint)

Duplicate check identifiers are rejected, so a check can never silently shadow another protection.
Deprecated checks must name their replacement; a required check is never deleted silently.

### Check categories

```text
IMPORT / STARTUP        DATABASE / MIGRATION     REPRODUCIBILITY
ARTIFACT INTEGRITY      DATA / SCHEMA            EXPERIMENT INTEGRITY
PIPELINE INTEGRITY      PROTOCOL INTEGRITY       EVIDENCE INTEGRITY
LINEAGE INTEGRITY       MODEL-CARD INTEGRITY     AUDIT INTEGRITY
QUANTUM INTEGRITY       DEPLOYMENT INTEGRITY
```

### Representative checks

| Check | Category | Severity | Verifies |
| --- | --- | --- | --- |
| `application_import` | IMPORT / STARTUP | REQUIRED | `from app.main import app, api` works from the deployment working directory |
| `application_startup_lifespan` | IMPORT / STARTUP | REQUIRED | real lifespan startup and `/api/health` without production secrets |
| `deployment_import_safety` | DEPLOYMENT INTEGRITY | REQUIRED | no `backend.app...` imports in production modules |
| `test_module_import_safety` | DEPLOYMENT INTEGRITY | ADVISORY | test modules use package-safe application imports |
| `database_schema_contract` | DATABASE / MIGRATION | REQUIRED | every ORM table/column materializes and every migration is recorded once |
| `database_migration_upgrade_path` | DATABASE / MIGRATION | REQUIRED (full) | re-applying additive migrations preserves legacy rows without fabricating provenance |
| `reproducibility_manifest_contract` | REPRODUCIBILITY | REQUIRED | manifest sections, identity-independent configuration fingerprints, structured integrity reporting |
| `fingerprint_canonicalization` | REPRODUCIBILITY | REQUIRED | canonical serialization is order-independent, value-sensitive and finite-safe |
| `fingerprint_determinism_matrix` | REPRODUCIBILITY | REQUIRED | nine scientific identities are deterministic and change-sensitive |
| `fingerprint_cross_process_determinism` | REPRODUCIBILITY | REQUIRED (full) | identical fingerprints in a fresh interpreter |
| `pipeline_version_immutability` | PIPELINE INTEGRITY | REQUIRED | published pipeline versions and stages reject mutation |
| `protocol_version_immutability` | PROTOCOL INTEGRITY | REQUIRED | published protocol versions reject mutation |
| `audit_event_immutability` | AUDIT INTEGRITY | REQUIRED | audit events reject update and delete |
| `lineage_relationship_immutability` | LINEAGE INTEGRITY | REQUIRED | identical relationships are idempotent, rewrites are rejected |
| `artifact_immutability` / `artifact_registry_contract` | ARTIFACT INTEGRITY | REQUIRED | content addressing, idempotency, conflicting-write rejection |
| `evidence_package_contract` | EVIDENCE INTEGRITY | REQUIRED | evidence-derived status, idempotency, new snapshots on new evidence, payload privacy |
| `lineage_integrity` | LINEAGE INTEGRITY | REQUIRED | resolvable nodes/edges, acyclicity, traversal, depth limiting, audit separation |
| `lineage_cycle_and_relationship_protection` | LINEAGE INTEGRITY | REQUIRED | cycle detection, self-reference and unsupported relationship rejection |
| `audit_timeline_contract` | AUDIT INTEGRITY | REQUIRED | reproducible event fingerprints, ordering, idempotency, reference resolution, secret-free metadata |
| `subgroup_contract` | EXPERIMENT INTEGRITY | REQUIRED | undefined metrics stay UNDEFINED, minimum-group withholding, deterministic study fingerprints |
| `dataset_quality_contract` | DATA / SCHEMA | REQUIRED | status vocabulary, defect detection, determinism, idempotency, artifact registration |
| `model_card_contract` | MODEL-CARD INTEGRITY | REQUIRED | deterministic cards, required sections, resolved references, no superiority language |
| `controlled_comparison_contract` | EXPERIMENT INTEGRITY | REQUIRED | parity controls, missing-evidence reporting, idempotency, no ranking |
| `quantum_provider_contract` | QUANTUM INTEGRITY | REQUIRED | registry loading, honest capability metadata, deterministic preflight |
| `quantum_diagnostics_contract` | QUANTUM INTEGRITY | REQUIRED | structured diagnostics preflight, unsupported model families refused |
| `experiment_integrity` / `legacy_compatibility` | EXPERIMENT INTEGRITY | REQUIRED | references resolve; legacy records load without invented history |
| `privacy_and_secret_safety` | DATA / SCHEMA | REQUIRED | no committed secrets, synthetic-only fixtures, no patient-level payloads |
| `scientific_schema_contracts` | DATA / SCHEMA | REQUIRED | schema versions and fixture fingerprints match the reviewed baseline |
| `verification_registry_contract` / `verification_result_contract` | IMPORT / STARTUP | REQUIRED | the verification framework itself is testable |

## Status and severity semantics

Status describes what happened to one check:

```text
PASS          the invariant held for the evaluated evidence
WARN          a non-blocking deviation or incomplete evidence
FAIL          the invariant was violated
SKIPPED       the check's precondition is genuinely absent (never for convenience)
UNVERIFIABLE  the invariant exists but the repository provides no evidence to evaluate it
```

Severity describes whether a non-passing outcome blocks the gate:

```text
REQUIRED   a FAIL blocks the pull request
ADVISORY   a WARN or FAIL is reported but does not block the pull request
```

Severity never represents scientific importance.

## CI profiles

| Profile | Command | Where it runs | Contents |
| --- | --- | --- | --- |
| `fast` | `python -m app.verification --profile fast` | every pull request, every push to `main` | import/startup, deployment import safety, schema and migration contract, reproducibility, fingerprints, immutability, pipeline/protocol/evidence/lineage/audit/subgroup/scorecard/model-card/comparison/quantum contracts, privacy, schema contracts, framework meta-checks |
| `full` | `python -m app.verification --profile full` | nightly schedule and manual runs | everything in `fast` plus the migration upgrade path and cross-process fingerprint determinism |

`scientific-ci.yaml` records the repository-level policy (profiles, blocking rules, artifact paths).
The check registry itself lives in code so there is exactly one authoritative source.

## Fixtures

`backend/app/verification/fixtures.py` builds deterministic synthetic fixtures only:

* a synthetic biomedical frame with a binary target, a subgroup field and one missing value
* a defective quality frame (missing values, duplicates, class imbalance, constant feature, non-finite values)
* canonical pipeline, protocol, manifest, audit-event, circuit, subgroup and comparison definitions
* persisted chains: minimal classical experiment, quantum/hybrid model, legacy experiment without
  newer references, rerun chain, controlled classical/quantum pair

No real biomedical dataset, patient-level record, production snapshot or secret is used. The privacy
check fails if verification fixtures start reading external data or if record-like files are committed
under `data/`.

## Reproducibility, fingerprint and immutability verification

* Every scientific identity is computed through the single shared implementation in
  `app/utils/serialization.py`. Scientific CI never adds a second hashing implementation.
* Determinism is verified per system (pipeline, protocol, subgroup study, dataset scorecard, audit
  event, quantum circuit, controlled-comparison index, reproducibility manifest) by recomputing the
  same canonical fixture twice and by confirming that a meaningful canonical change changes the value.
* Immutability is verified by creating, publishing and then attempting to mutate pipeline versions,
  protocol versions, audit events, lineage relationships and artifacts; every attempt must be rejected.
* Large models are never retrained to prove reproducibility during a pull request.

## Expected versus generated fingerprints

`scientific-ci-baseline.json` and `backend/app/verification/baseline.py` intentionally store canonical
fixture fingerprints and scientific schema versions. Each value derives from a fixed synthetic fixture
with no clock, identity, runtime or environment input, so a change means the scientific identity itself
changed and must be reviewed. `scientific_schema_contracts` fails when a value changes without the
baseline being updated in the same pull request, which is how scientific invariants stay reviewable.

## Failure interpretation

Every non-passing required check prints an actionable block:

```text
Scientific CI FAILURE

Check:
protocol_version_immutability

Category:
PROTOCOL INTEGRITY

Status:
FAIL

Failure category:
SCIENTIFIC_REGRESSION

Reason:
Published Protocol Version was mutated.

Expected:
immutable definition

Observed:
fingerprint changed from 86bc8060... to 00000000...
```

Failure categories distinguish what a developer must fix:

```text
SCIENTIFIC_REGRESSION              a protected scientific invariant was violated
APPLICATION_FAILURE                application code fails to import, start or behave as specified
TEST_FAILURE                       the ordinary test suite failed
MIGRATION_FAILURE                  schema or migration application failed
ENVIRONMENT_FAILURE                a required dependency or configuration is unavailable
VERIFICATION_INFRASTRUCTURE_FAILURE the verification framework itself misbehaved
```

Exit codes:

```text
0  every required check passed
1  at least one required check failed
2  the verification infrastructure failed
```

Checks are never retried automatically: retries would hide nondeterminism. Each check has a
per-check timeout so a hung check cannot block the pipeline indefinitely.

## Privacy and security

* Scientific CI never requires production secrets; it runs with an isolated storage root, an empty
  API token and no external services.
* CI logs contain structured summaries; detailed JSON is uploaded as a CI artifact.
* The privacy check scans for committed credentials, private keys and provider tokens, and verifies
  that generated evidence manifests, lineage snapshots and model cards contain no patient-level keys.
* Workflows use `permissions: contents: read` and never execute untrusted pull-request code with
  write permissions. Nothing is deployed or merged by Scientific CI.

## GitHub Actions

`.github/workflows/scientific-ci.yml`:

```text
pull_request -> fast profile  (blocking gate)
push main    -> fast profile  (regression gate)
schedule     -> full profile  (nightly)
manual       -> full profile
```

Artifacts uploaded: `scientific-ci-report.json`, `scientific-ci-manifest.json`. The workflow writes a
concise summary into the job summary instead of raw tracebacks.

`.github/workflows/ci.yml` runs the ordinary gates: backend tests (`-m "not quantum"`) with a JUnit
report, and frontend `npm ci`, `npm test`, `npm run build`.

The workflow files are staged in `ci/workflows/` and must be installed at `.github/workflows/` once,
because GitHub only executes workflows from that directory (see `ci/README.md` for the one-command
installation). The gate itself is independent of the workflow location: `python -m app.verification`
runs exactly what CI runs.

## Limitations

* Scientific CI verifies implementation-level invariants. It cannot and does not validate scientific
  correctness, clinical validity, model quality or quantum advantage.
* The migration upgrade check re-applies the additive migrations on a database that already contains
  legacy rows; it does not replay a historical production snapshot.
* Quantum checks verify the provider architecture, capability metadata, preflight and diagnostics
  contracts using local simulators. No cloud quantum hardware is contacted and no long quantum job is
  executed in ordinary CI.
* Heavy scientific computation (full training, long studies, large datasets) is deliberately out of
  scope; the existing test suite covers those behaviours separately.
* A green Scientific CI run states only that the configured automated scientific integrity checks held.
