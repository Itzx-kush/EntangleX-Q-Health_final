-- Private, authenticated saved research-report artifacts.
-- Canonical experiments and scientific evidence remain in the Q-Health backend.

create extension if not exists pgcrypto;

create table if not exists public.saved_research_reports (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  experiment_id text not null,
  evidence_package_id text,
  report_artifact_id text,
  report_fingerprint text not null check (report_fingerprint ~ '^[0-9a-f]{64}$'),
  evidence_package_fingerprint text,
  report_version text not null,
  report_title text not null check (char_length(report_title) between 1 and 240),
  dataset_name text,
  experiment_name text,
  primary_result jsonb,
  generated_at timestamptz not null,
  saved_at timestamptz not null default now(),
  storage_reference text not null,
  content_type text not null check (content_type = 'application/pdf'),
  file_size bigint not null check (file_size > 0),
  integrity_hash text not null check (integrity_hash ~ '^[0-9a-f]{64}$'),
  status text not null default 'active' check (status in ('active', 'deleted')),
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint saved_report_storage_is_relative check (storage_reference !~ '(^/|://|\\.\\.)'),
  constraint saved_report_primary_result_object check (primary_result is null or jsonb_typeof(primary_result) = 'object')
);

comment on table public.saved_research_reports is
  'Private user-owned metadata for immutable EntangleX PDF research-report snapshots stored in a private Supabase Storage bucket.';
comment on column public.saved_research_reports.owner_user_id is
  'Owner derived by the backend from a cryptographically verified Supabase access token; RLS and revoked client grants add defense in depth.';

create unique index if not exists saved_reports_owner_snapshot_active
  on public.saved_research_reports (owner_user_id, experiment_id, report_fingerprint, report_version)
  where status = 'active';
create unique index if not exists saved_reports_storage_reference
  on public.saved_research_reports (storage_reference);
create index if not exists saved_reports_owner_saved_at
  on public.saved_research_reports (owner_user_id, saved_at desc)
  where status = 'active';
create index if not exists saved_reports_owner_experiment
  on public.saved_research_reports (owner_user_id, experiment_id)
  where status = 'active';

alter table public.saved_research_reports enable row level security;
alter table public.saved_research_reports force row level security;
revoke all on table public.saved_research_reports from anon, authenticated;

drop policy if exists "saved_reports_select_own" on public.saved_research_reports;
create policy "saved_reports_select_own" on public.saved_research_reports
  for select to authenticated using (auth.uid() = owner_user_id);
drop policy if exists "saved_reports_insert_own" on public.saved_research_reports;
create policy "saved_reports_insert_own" on public.saved_research_reports
  for insert to authenticated with check (auth.uid() = owner_user_id and status = 'active');
drop policy if exists "saved_reports_update_own" on public.saved_research_reports;
create policy "saved_reports_update_own" on public.saved_research_reports
  for update to authenticated
  using (auth.uid() = owner_user_id)
  with check (auth.uid() = owner_user_id);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('saved-research-reports', 'saved-research-reports', false, 26214400, array['application/pdf'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

-- Private report objects are intentionally backend-only. The service role bypasses
-- Storage RLS after the API has verified the caller and checked report ownership.
drop policy if exists "saved_report_objects_select_own" on storage.objects;
drop policy if exists "saved_report_objects_insert_own" on storage.objects;
drop policy if exists "saved_report_objects_delete_own" on storage.objects;
