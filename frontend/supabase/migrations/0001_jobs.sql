create table jobs (
  id         uuid primary key default gen_random_uuid(),
  status     text not null default 'pending',
  error      text,
  inputs     jsonb not null,
  output_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by uuid not null references auth.users(id) on delete cascade
);

create index jobs_created_by_created_at_idx on jobs (created_by, created_at desc);

create or replace function set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

create trigger jobs_set_updated_at before update on jobs
  for each row execute function set_updated_at();

alter table jobs enable row level security;

create policy "users see own jobs"
  on jobs for select using (auth.uid() = created_by);

create policy "users insert own jobs"
  on jobs for insert with check (auth.uid() = created_by);
