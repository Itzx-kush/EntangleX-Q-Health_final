# Authentication and personal research workspace

EntangleX Q-Health supports two frontend entry paths:

- **Continue with Google** creates an authenticated Supabase session and opens a personal EntangleX workspace.
- **Continue without signing in** opens the existing anonymous research prototype and preserves its existing backend/API behavior.

Authentication is optional. It does not protect, proxy, or change the existing Q-Health research APIs. The existing backend remains the source of truth for datasets, experiments, models, predictions, explanations, quantum execution, and scientific evidence.

## Supabase and Google setup

1. Create or select a Supabase project.
2. In Supabase Authentication, enable the Google provider.
3. Configure the Google OAuth client ID and client secret in the **Supabase dashboard**, never in frontend source or a `VITE_*` variable.
4. Add the deployed application callback/redirect URL to the Supabase and Google provider allowlists. Include the local Vite URL when testing locally.
5. Copy `frontend/.env.example` to `frontend/.env.local` and set only the public browser values:

   ```dotenv
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-public-anon-key
   ```

6. Apply the SQL files in `supabase/migrations` in filename order.

Do not place the Supabase service-role key, Google client secret, database password, backend API token, or any other privileged credential in the frontend environment. Vite exposes every `VITE_*` value to the browser.

Without Supabase configuration, the entry screen explains that Google sign-in is unavailable and leaves guest access enabled.

## Session behavior

`AuthProvider` is the single frontend source of truth for the Supabase session, user, loading state, errors, Google sign-in, sign-out, and guest access. Supabase owns token persistence and refresh; the application does not copy OAuth tokens into custom storage or logs.

The authenticated shell uses the Google-provided name, email, and avatar when present, with a deterministic initials fallback. Sign-out removes authenticated UI and returns to the entry experience. Supabase auth-state events provide refresh and multi-tab session synchronization.

## Personal research history

The `research_activity` table stores private, metadata-only references for meaningful research actions:

- experiment creation;
- research predictions;
- explanations;
- quantum circuit activity;
- imported guest-session summaries.

The existing EntangleX backend still owns the underlying scientific records and calculations. Supabase history stores internal routes, backend reference IDs, status, timestamps, and bounded summaries. It intentionally excludes raw uploaded datasets, patient-like inputs, feature values or names from guest drafts, complete predictions, explanation arrays, model metric payloads, circuit text, credentials, and OAuth tokens.

## Guest-to-account continuity

Guest mode creates a per-tab session identifier in `sessionStorage`. When eligible local research context exists, **Sign in to save** snapshots only safe reference metadata and the current internal route before starting Google OAuth.

After Supabase restores the authenticated session, the application upserts one user-owned `session` activity using a stable per-session idempotency key. Refreshes, React Strict Mode, retries, and callback reprocessing therefore do not create duplicate imported-session rows. On failure, the local guest draft remains available and the user can retry. A successful import keeps the active research configuration in place so the user remains contextually oriented; dismissing the confirmation clears only migration bookkeeping.

## Ownership and Row Level Security

`research_activity.user_id` defaults to `auth.uid()`. The frontend never accepts an owner ID from guest storage and does not send a `user_id` during inserts.

Row Level Security is enabled and forced. Policies allow authenticated users to select, insert, update, and delete only rows where `auth.uid() = user_id`; the anonymous role has no table privileges. Frontend user-scoped queries and user-keyed TanStack Query caches are defense in depth, not the authorization boundary. Private cached history is removed when the authenticated user changes or signs out.

Before production use, validate the policies with two real test accounts:

1. User A creates a history record.
2. User B cannot select, update, or delete User A's record.
3. An anonymous client cannot read or write `research_activity`.
4. User A can still read their own record after signing in again.

## Local validation

From `frontend`:

```bash
npm ci
npm run build
npm test
npm audit --omit=dev
```

Production OAuth and RLS verification require a configured Supabase project and Google OAuth client. Do not test migration using real health information.