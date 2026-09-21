# Local deployment

## Supported topology

The generated configuration targets one workstation, one backend process, one SQLite database and one bounded worker. It is not a shared clinical service. Keep bindings at loopback and use the frontend's `/api` proxy. Backend storage is resolved against the repository root; do not rely on the shell working directory.

Native installation commands are in the root README. CPython 3.11 and Node 22.12.0 in the Node 22.x line are assumed. The normal full install includes quantum, SHAP and test dependencies; a classical-only path is also documented. The direct dependency set and frontend lockfile have been installed and import-checked in a clean environment; see `docs/verified_environment.md`. Native application/runtime verification is recorded in `docs/task1_final_verification.md`. Docker execution was not possible in final closure because the Docker CLI/daemon was unavailable.

## Docker structure

`backend/Dockerfile` uses Python 3.11.16 slim, installs backend manifests and runs as nonroot UID 10001. It creates an owned `/runtime` tree for SQLite and artifacts. `frontend/Dockerfile` builds with Node 22.12.0 and the committed `package-lock.json` via `npm ci`, then serves static files through unprivileged Nginx on 8080. The Dockerfiles and compose configuration passed static consistency review; image/runtime execution remains unverified because Docker was unavailable. Immutable image digests are still a deployment-hardening consideration.

Compose publishes only `127.0.0.1:8000` and `127.0.0.1:8080`. The frontend waits for the backend HTTP healthcheck, which verifies reachability only. Nginx proxies `/api/`, applies a same-origin content-security policy, limits upload bodies and disables access logs. The backend independently enforces body size and authorization. `.env` is excluded from the Docker build context and supplied at runtime. Compose validation/build/startup/proxy checks were not executed because Docker was unavailable.

```bash
# From project root, after creating .env
docker compose up --build
# Inspect the current local services
docker compose ps
# Stop without deleting data
docker compose down
```

The named volume `qhealth_data` contains all runtime data. `docker compose down -v` is destructive. A bind-mounted directory, when deliberately substituted, must be writable by the backend UID and protected from other users. Do not mount arbitrary user-writable model files into the trusted artifacts directory.

## Jobs and shutdown

Use one uvicorn worker. Hot reload or multiworker deployment can abandon or duplicate in-process ownership assumptions. Shutdown requests cancellation at safe boundaries and waits for the running executor. Compose grants 120 seconds before force termination; a long simulator call may exceed this, after which restart records active jobs as interrupted. This is explicit loss-of-worker handling, not a durable distributed queue or automatic resume.

Keep sample budgets modest and monitor real memory/CPU consumption. The source bounds input sizes, row/column counts, qubits, optimizer iterations and queued jobs, but does not impose OS-level per-job resource quotas. Prediction/explanation requests are synchronous and may be costly for quantum models.

## Data backup and removal

Stop the backend before copying the whole runtime directory or named volume. Preserve database, dataset CSVs, model artifacts and experiment snapshots together; a model needs its source hash and training indices for later explanation. SQLite WAL files may be active until clean shutdown. Stored model hashes detect accidental artifact changes, not malicious replacement of both the database and artifact by a filesystem administrator.

Deletion of an unreferenced dataset is supported through the API. There is no retention scheduler or complete regulatory deletion workflow. Referenced datasets are retained to prevent broken experiment provenance. Plan storage retention before private-data use.

## Public deployment is outside the current security boundary

A token is not user management, access control, tenant isolation or a compliance program. Public deployment requires a reviewed authentication layer, TLS, authorization, audit policies, encrypted storage, validated backups, request/rate quotas, deployment hardening, monitoring and threat assessment. Clinical deployment additionally requires appropriate scientific and regulatory work that this prototype does not supply.
