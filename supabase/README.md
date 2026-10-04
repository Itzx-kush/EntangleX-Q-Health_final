# EntangleX Supabase data layer

Supabase is used only for authenticated identity and private, user-owned research metadata. The existing EntangleX backend remains the source of truth for datasets, experiments, model execution, predictions, explanations, quantum execution, and scientific evidence.

## Migration

Apply the migrations in filename order to the same Supabase project configured by `VITE_SUPABASE_URL`:

1. `migrations/20261002170000_create_research_activity.sql`
2. `migrations/20261002190000_allow_guest_session_activity.sql`
3. `migrations/20261004133000_create_saved_research_reports.sql`

The migration creates one deliberately small table:

- `research_activity` — a private activity stream containing backend references, status, routes, timestamps, and small non-sensitive summaries.

It does **not** store raw uploaded datasets, patient-like prediction inputs, complete prediction payloads, explanation arrays, model metrics, circuit text, tokens, or backend artifacts.

Guest-to-account continuity creates at most one idempotent `session` activity per intentionally active browser tab. It stores only an internal return route, backend references, and bounded configuration summaries. Feature names, raw samples, credentials, transient UI state, and OAuth data are excluded. Guest state is retained when persistence fails.

## Ownership and RLS

`user_id` defaults to `auth.uid()`. Row Level Security is enabled and forced. Authenticated users may select, insert, update, and delete only rows where `auth.uid() = user_id`. The anonymous role receives no table privileges.

The frontend also constrains history reads to the active authenticated user, but this is defense in depth—not the security boundary.

## Idempotency and indexing

Backend entities with stable identifiers use a per-user `idempotency_key`, preventing duplicate experiment, explanation, and imported guest-session records. Prediction and generated-circuit actions do not expose backend event IDs, so each successful explicit user action becomes a distinct database-timestamped activity.

Indexes support the actual query patterns:

- latest activity by user;
- latest activity by user and type;
- user-owned reference lookup;
- per-user idempotency.

## Required external configuration

1. Apply the SQL migration to the configured Supabase project.
2. Keep only the public URL and anon/publishable key in the frontend environment.
3. Never use a service-role key in the browser.
4. Validate the policies with two real test users before production deployment.

## Saved research reports

Apply `migrations/20261004133000_create_saved_research_reports.sql` after the research-activity migrations. It creates:

- `saved_research_reports`, a private user-owned metadata table with RLS;
- a private `saved-research-reports` Storage bucket;
- owner-scoped table and object policies based on `auth.uid()`;
- an active-snapshot uniqueness rule to prevent duplicate saves.

The backend cryptographically verifies the Supabase access token, derives the owner from its `sub` claim, and uses a backend-only service-role credential for the owner-filtered PostgREST and private Storage operations. The service-role credential is never returned to or exposed in the browser.

Backend-only Render variables required for this feature:

- `QHEALTH_SUPABASE_URL` — the same Supabase project URL used by the frontend;
- `QHEALTH_SUPABASE_SERVICE_ROLE_KEY` — the project service-role key; configure it only on the backend and never in any `VITE_` variable;
- `QHEALTH_SUPABASE_JWT_AUDIENCE` — optional, defaults to `authenticated`;

The existing frontend variables (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`) remain unchanged. Never configure a Supabase service-role key in the browser.
