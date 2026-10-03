# Model Cards

EntangleX Q-Health Model Cards are immutable, structured evidence summaries for existing `ModelRecord` records. They document what the repository has persisted and make missing evidence explicit. They do not rank models or establish clinical safety, diagnostic efficacy, deployment readiness, population generalization, or quantum advantage.

## Architecture

- Schema version: `model_card_v1`
- Assembly: `backend/app/model_cards/service.py`
- Lineage: `Experiment → Run → ModelRecord → Artifact`
- Artifact type: `model_card`
- Source evidence: dataset/version, ConditionTask, run configuration and provenance, model metrics, multi-seed studies, calibration, threshold analysis, external validation, distribution shift, grouped validation metadata, robustness records, and quantum/provider provenance.

The service uses allowlisted fields. Raw biomedical rows, patient/group identifiers, credentials, tokens, and environment values are excluded. Group-aware cards expose only strategies and aggregate counts.

## Completeness states

`COMPLETE`, `COMPLETE_WITH_LIMITATIONS`, `INCOMPLETE_EVIDENCE`, and `UNAVAILABLE` describe card completeness and evidence availability, never model quality. Sections use explicit states including `available`, `not_available`, `not_applicable`, `not_recorded`, `not_configured`, and `not_yet_evaluated`.

## Determinism and persistence

The canonical card derives a source fingerprint from persisted source evidence. `card_id` and the artifact operation key incorporate that fingerprint. Repeated reads with unchanged evidence return the same immutable artifact; changed evidence creates a new version instead of mutating the previous card. `generated_at` is derived from persisted source timestamps rather than request time.

## API

- `GET /api/models/{identity}/card` — canonical card and artifact identity
- `GET /api/models/{identity}/card/summary` — compact UI summary
- `GET /api/models/{identity}/card/evidence` — evidence references, availability, and gaps
- `GET /api/model-cards?limit=50&offset=0` — paginated persisted cards

All routes use the normal authenticated `/api` router and existing safe error contracts.

## Frontend

The experiment model inspector contains a **Model Card** panel. It distinguishes available, unavailable, not applicable, and limited evidence without manufacturing placeholder metrics.

## Scientific limitations

Cards summarize only evidence associated with the selected model. Absence remains absence. Internal, external, seed, calibration, threshold, shift, and grouped results remain separately identified and are not collapsed into an overall score. Quantum provider use is execution provenance, not evidence of quantum advantage.