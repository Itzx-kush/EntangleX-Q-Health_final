-- EntangleX Q-Health: private, metadata-only research history.
-- Core scientific results remain in the existing EntangleX backend.

create extension if not exists pgcrypto;

create table if not exists public.research_activity (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  activity_type text not null check (activity_type in ('experiment', 'prediction', 'explanation', 'quantum', 'session')),
  title text not null check (char_length(title) between 1 and 160),
  status text,
  occurred_at timestamptz not null default now(),
  route text not null,
  reference_id text,
  experiment_id text,
  model_id text,
  dataset_id text,
  method text,
  metadata jsonb not null default '{}'::jsonb,
  idempotency_key text,
  created_at timestamptz not null default now(),
  constraint research_activity_route_is_internal check (route like '/%'),
  constraint research_activity_metadata_is_object check (jsonb_typeof(metadata) = 'object')
);

comment on table public.research_activity is
  'Private EntangleX research metadata and backend references. Raw health/sample inputs and full scientific result payloads are intentionally excluded.';
comment on column public.research_activity.user_id is
  'Owner derived from the authenticated Supabase session; defaults to auth.uid().';
comment on column public.research_activity.metadata is
  'Small, non-sensitive configuration/result summary only. Never store raw patient-like inputs.';

create unique index if not exists research_activity_user_idempotency_key
  on public.research_activity (user_id, idempotency_key);

create index if not exists research_activity_user_occurred_at
  on public.research_activity (user_id, occurred_at desc);

create index if not exists research_activity_user_type_occurred_at
  on public.research_activity (user_id, activity_type, occurred_at desc);

create index if not exists research_activity_user_reference
  on public.research_activity (user_id, reference_id)
  where reference_id is not null;

alter table public.research_activity enable row level security;
alter table public.research_activity force row level security;

revoke all on table public.research_activity from anon;
grant select, insert, update, delete on table public.research_activity to authenticated;

drop policy if exists "research_activity_select_own" on public.research_activity;
create policy "research_activity_select_own"
  on public.research_activity
  for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists "research_activity_insert_own" on public.research_activity;
create policy "research_activity_insert_own"
  on public.research_activity
  for insert
  to authenticated
  with check (auth.uid() = user_id);

drop policy if exists "research_activity_update_own" on public.research_activity;
create policy "research_activity_update_own"
  on public.research_activity
  for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "research_activity_delete_own" on public.research_activity;
create policy "research_activity_delete_own"
  on public.research_activity
  for delete
  to authenticated
  using (auth.uid() = user_id);
