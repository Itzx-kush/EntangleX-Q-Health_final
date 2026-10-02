-- Phase 4: permit one metadata-only activity row for an imported guest session.
-- Safe to apply after the Phase 3 research_activity migration.

alter table public.research_activity
  drop constraint if exists research_activity_activity_type_check;

alter table public.research_activity
  add constraint research_activity_activity_type_check
  check (activity_type in ('experiment', 'prediction', 'explanation', 'quantum', 'session'));