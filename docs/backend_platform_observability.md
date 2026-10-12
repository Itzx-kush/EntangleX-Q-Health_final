# Backend Platform 2.0: Performance, Observability, Resilience & Dashboard-Ready Telemetry

## 1. Executive Summary

Backend Platform 2.0 upgrades the EntangleX Q-Health backend into a production-grade, observable, resilient research platform without altering any scientific algorithms, training routines, quantum circuits, thresholds, or benchmark outcomes.

### Core Architecture Principles
1. **Scientific Algorithm Invariance**: Machine learning architectures, quantum circuits, calibration mathematics, subgroup analyses, and model metrics remain strictly untouched.
2. **Zero External APM Bloat**: Lightweight in-process registry with zero external monitoring stack dependencies (no mandatory Prometheus, Grafana, or Datadog daemons).
3. **Bounded In-Memory Structures**: Memory footprint is bounded through rolling windows and bounded ring buffers to prevent memory growth over long workstation uptimes.
4. **Cardinality Protection**: Dynamic URLs (UUIDs, 64-char hashes, integer IDs) are normalized into route templates (`/api/experiments/{id}`) to eliminate metric cardinality explosion.
5. **Authoritative SQLite WAL with Optional Redis Acceleration**: SQLite in Write-Ahead Logging (WAL) mode remains authoritative; Redis is strictly an optional accelerator.
6. **Privacy & HIPAA/Biomedical Safety**: Raw medical data, patient records, auth tokens, passwords, and connection strings are never logged, reflected, or cached globally.

---

## 2. Platform Telemetry & Observability Architecture

### 2.1 In-Process Telemetry Registry (`app.telemetry.registry`)
- Thread-safe in-process metrics recording:
  - Aggregate request volume, error counts, error rates (`error_rate`).
  - Latency percentiles: Average (`avg_ms`), P50 (`p50_ms`), P95 (`p95_ms`), and P99 (`p99_ms`).
  - Rolling operational window (configurable via `telemetry_window_seconds`, default 300s).
  - Lifetime counters (`lifetime_total`, `lifetime_errors`).
  - Per-route breakdown with identical percentile and error stats.

### 2.2 Route Normalization
`TelemetryRegistry.normalize_route(method, path)` normalizes paths:
- UUID patterns `[0-9a-fA-F]{8}-...` -> `{id}`
- SHA-256 hashes `[0-9a-fA-F]{64}` -> `{hash}`
- Numeric identifiers `/\d+` -> `/{id}`
- Query strings `?...` stripped before categorization.

### 2.3 Probes & Health Taxonomy
- **Liveness Probe**: `GET /api/health`
  - Verifies process is alive and returns basic deployment metadata.
- **Readiness Probe**: `GET /api/health/ready`
  - Validates SQLite database connectivity (`SELECT 1`) and storage directories accessibility. Returns HTTP 200 when ready, HTTP 503 if degraded.
- **System Status**: `GET /api/system/status`
  - Optimized dashboard summary with indexed `GROUP BY status` query (eliminating legacy full-table ORM loading).
- **Telemetry Endpoint**: `GET /api/system/telemetry`
  - Exposes dashboard-ready request latencies, cache metrics, job queue capacity, worker status, and dependency health.
- **Diagnostics Endpoint**: `GET /api/system/diagnostics`
  - Read-only diagnostics for operators reporting environment, database latency, journal mode, storage bytes, and dependency states.

---

## 3. Pluggable Safe Caching Layer (`app.cache`)

- **In-Memory LRU Cache (`InMemoryCache`)**:
  - Thread-safe LRU cache with configurable entry cap (`cache_max_entries`, default 2000) and TTL (`cache_ttl_seconds`, default 300s).
  - Precise metrics tracking: hits, misses, hit rate %, evictions, and cache size.
  - Granular prefix invalidation (`invalidate_prefix(prefix)`).
- **Pluggable Acceleration (`PluggableCache`)**:
  - In-memory authority with transparent optional Redis read/write pass-through.
  - Automatic fallback if Redis is disabled or temporarily offline.
- **Deterministic Key Design**:
  - Immutable evidence packages: `evidence_package:{id}:{fingerprint}` (1 hour TTL).
  - Built-in dataset catalog: `catalog:builtin:{include_readiness}` (60s TTL).
  - Telemetry I/O probes: `telemetry:probes` (2s TTL to prevent rapid-poll DB churn).

---

## 4. Bounded Sliding Window Rate Limiting (`app.ratelimit`)

- **Bounded Memory Sliding Window (`SlidingWindowRateLimiter`)**:
  - Thread-safe sliding window tracking requests per identity within a rolling time window.
  - Tracks up to `max_identities` (default 5,000) using LRU identity eviction.
  - Anonymized identity: hashes bearer tokens or client IPs so credentials are never stored.
- **Guarded Endpoints**:
  - `POST /api/training/jobs` (training enqueue)
  - `POST /api/ai/chat` (Groq assistant chat, also protected with a 15s timeout)
  - `POST /api/datasets/inspect` (CSV upload inspection)
  - `POST /api/datasets/upload` (CSV registration)
  - `POST /api/studies/multi-seed` (multi-seed study enqueue)
- **Standardized Error Handling**:
  - Emits HTTP 429 with `{ "error": { "code": "rate_limited", "message": "...", "request_id": "..." } }`.

---

## 5. Database Performance & Index Migration

### 5.1 Query Optimization
- Replaced `select(Job)` full table scan in `/api/system/status` with `select(Job.status, func.count()).group_by(Job.status)`.

### 5.2 Schema Migration (`20261011_01_platform_observability_indexes`)
Additive, non-destructive index migrations:
- `ix_experiments_created_at ON experiments(created_at)`
- `ix_experiments_status ON experiments(status)`
- `ix_models_status ON models(status)`
- `ix_models_dataset_id ON models(dataset_id)`
- `ix_models_created_at ON models(created_at)`
- `ix_jobs_status ON jobs(status)`
- `ix_jobs_created_at ON jobs(created_at)`

---

## 6. Scientific Non-Claims & Research Prototype Notice

EntangleX Q-Health is an experimental research and decision-support prototype. It is NOT certified as a medical device or clinical diagnostic tool. All metrics and telemetry reported by Platform 2.0 measure computational performance, database latency, and system health—never clinical validity.
