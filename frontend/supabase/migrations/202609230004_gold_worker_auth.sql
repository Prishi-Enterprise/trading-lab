create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table if not exists private.worker_secrets (
  worker_name text primary key,
  secret_value text not null,
  created_at timestamptz not null default now()
);

revoke all on table private.worker_secrets from public, anon, authenticated;

insert into private.worker_secrets (worker_name, secret_value)
values ('gold-tracker', encode(extensions.gen_random_bytes(32), 'hex'))
on conflict (worker_name) do nothing;

create or replace function public.verify_worker_secret(requested_worker text, candidate_secret text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from private.worker_secrets
    where worker_secrets.worker_name = requested_worker
      and worker_secrets.secret_value = candidate_secret
  );
$$;

revoke all on function public.verify_worker_secret(text, text) from public, anon, authenticated;
grant execute on function public.verify_worker_secret(text, text) to service_role;
