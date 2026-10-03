# Resumable job execution

A durable `Job` can continue from its newest compatible validated checkpoint. Resume preserves the Job ID and completed logical units; retry creates a new Job/Run and starts again.

## Lifecycle and controls

Jobs use guarded states including `queued`, `running`, `checkpointing`, `pause_requested`, `paused`, `recoverable`, `resuming`, `cancel_requested`, `cancelled`, `failed`, `partial`, and `succeeded`. Invalid transitions are rejected. Pause and cancellation are cooperative and take effect only at a safe handler boundary. Pausing requires a validated checkpoint.

## Checkpoints

Checkpoint JSON stores a phase, stable completed-unit keys, deterministic input/configuration fingerprints, sequence, and artifact integrity references. Publishing occurs only after outputs are durable: persist output, verify it, hash canonical state, insert metadata, then mark valid in one transaction. Resume scans newest-first, invalidates corrupt/incompatible candidates, and falls back to the preceding valid checkpoint.

## Leases, heartbeat, and stale recovery

An atomic conditional update grants one worker a time-limited lease. Heartbeats extend it. Expired active leases are classified `worker_lost` and made `recoverable` without launching duplicate work. The current deployment remains the existing bounded single-process worker; startup expires predecessor-process leases and restores queued jobs.

## Idempotency and partial work

Each unit has a unique deterministic key such as `training:model:<model-id>`. Durable successful units are skipped on resume. Intermediate checkpoint outputs remain distinct from final results. `partial` is not presented as complete.

## API

- `GET /api/jobs/{id}` and `/status`
- `GET /api/jobs/{id}/progress`
- `GET /api/jobs/{id}/checkpoints`
- `GET /api/jobs/{id}/history`
- `POST /api/jobs/{id}/pause|resume|cancel|retry`

Repeated pause/cancel calls are safe. Leases prevent concurrent resumes. Retry accepts the existing `Idempotency-Key` convention and defaults to a stable source-job key.

## Configuration

- `QHEALTH_JOB_LEASE_SECONDS` (default `120`)
- `QHEALTH_JOB_MAX_ATTEMPTS` (default `3`)
- `QHEALTH_JOB_MAX_RESUME_ATTEMPTS` (default `5`)

## Security and limitations

Public responses omit worker ownership and filesystem paths. Logs contain opaque identifiers and exception types, never biomedical rows or credentials. Prompt 16 wires only the existing training handler; future workflows may implement `JobHandler`. A model fit is the smallest training recovery unit. SQLite and the in-process executor remain the current single-workstation architecture.
