# SIH Phase 1 — Platform and Research Experience Upgrade

## Objective

Phase 1 upgrades the existing EntangleX Q-Health prototype into a judge-ready research
workspace without replacing its API, training pipeline, model registry, or scientific
boundaries. The implementation is aligned with the Smart India Hackathon 2026 criteria:
novelty, complexity, clarity/detail, feasibility, practicability, sustainability, scale of
impact, user experience, and future progression.[^https://sih.gov.in/letters/2026/SIH%202026%20Guidelines.pdf]

## Frontend

- Replaced the horizontal-only shell with a responsive research workspace:
  - grouped left navigation for Research, Modeling, Interpretation, Experiments, and Presentation;
  - sticky top bar with breadcrumbs, connection state, search, command palette, settings, and inspector controls;
  - collapsible desktop sidebar and mobile navigation drawer;
  - bottom system-status strip and persistent research disclaimer.
- Added a live context inspector backed by `/api/health`, `/api/summary`, `/api/training/jobs`, and
  `/api/system/status`. It shows registry counts, active jobs, storage readiness, and the
  simulator/hardware boundary without exposing paths or secrets.
- Added a keyboard-accessible command palette (`Ctrl/Cmd + K`) for research navigation and
  presentation mode.
- Added the SIH Demo Center as a real navigation rail over the existing workflow. Each step
  opens the corresponding product screen; it does not fabricate stage completion or metrics.
- Added a settings center for research-light/deep-research theme, compact/comfortable density,
  reduced motion, and inspector visibility. Preferences are local UI state only.
- Added a presentation-mode link and the existing backend state to the first-view shell so a
  judge can understand the product without reading source code.

## Backend

- Added `GET /api/system/status`, a safe read-only endpoint for:
  - database and storage availability;
  - quantum package availability and execution boundary;
  - supported classical and quantum model identifiers;
  - queued, running, and active job counts.
- No credentials, environment variables, private filesystem paths, biomedical records, or raw
  model inputs are returned.
- Added focused API coverage for the status endpoint.

## Architecture

The product now combines:

1. **Research workspace information architecture** — grouped navigation, registry-first pages,
   detail views, and contextual inspection.
2. **Q-Health domain functionality** — existing dataset validation, leakage-safe preprocessing,
   classical/quantum training, comparison, explainability, prediction, and experiment reports.
3. **React Bits-inspired interaction layer** — existing reveal, spotlight, glow, orbit, glare,
   hover, shimmer, gradient, and reduced-motion patterns retained and placed inside a more
   coherent shell.
4. **SIH presentation layer** — a real guided demo route that transitions into the underlying
   product instead of a disconnected mock presentation.

## Verification

Commands run on the Phase 1 branch:

```text
cd frontend && npm ci
cd frontend && npm run build
cd frontend && npm test -- --run
cd backend && ../.venv/bin/python -m pytest -q -m "not quantum"
```

Results at the time of writing:

- Frontend build: passed; Vite emitted a non-blocking bundle-size warning.
- Frontend tests: 3 passed.
- Backend non-quantum regression: 66 passed, 34 deselected, one dependency deprecation warning.
- The local Vite server responded successfully to `curl` on port 5173. Shared-browser visual
  navigation was not completed in this sandbox because the browser could not reach the local
  loopback address.

## Scientific boundaries

The upgrade preserves the existing boundary statements:

- a research prototype is not a diagnostic or treatment system;
- local quantum simulation is not real quantum hardware;
- circuit depth, gate count, or a quantum label does not prove quantum advantage;
- feature influence is not biological causation;
- model metrics are runtime measurements under explicit dataset, split, preprocessing, and
  configuration conditions.

## Phase 2 priorities

1. Run a live end-to-end smoke test with the target Python environment, including a bounded QNN
   path where dependencies are installed.
2. Add route-level component tests for the command palette, settings persistence, inspector
   states, and demo rail.
3. Perform headed visual QA at 1440px, 1280px, tablet, and narrow mobile widths.
4. Split the large frontend bundle and verify route-level lazy loading.
5. Add report navigation from the Demo Center after an actual experiment is available.
6. Re-check Docker runtime and deployment hardening in the target environment.
