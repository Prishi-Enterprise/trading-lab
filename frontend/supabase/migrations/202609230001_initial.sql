create extension if not exists citext with schema extensions;

create table public.trading_members (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique references auth.users(id) on delete set null,
  email extensions.citext not null unique,
  display_name text not null,
  role text not null default 'viewer' check (role in ('owner', 'viewer')),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.paper_updates (
  as_of date primary key,
  recorded_at timestamptz not null,
  status text not null check (status in ('verified', 'blocked', 'complete')),
  headline text not null,
  summary text not null,
  portfolio jsonb not null default '{}'::jsonb,
  signals jsonb not null default '{}'::jsonb,
  details jsonb not null default '{}'::jsonb,
  source text not null default 'paper-trading recorder',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.trading_members enable row level security;
alter table public.paper_updates enable row level security;

create or replace function public.is_trading_member()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.trading_members
    where user_id = (select auth.uid()) and active
  );
$$;

create or replace function public.claim_trading_membership()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  claimed integer;
begin
  if auth.uid() is null or auth.email() is null then
    return false;
  end if;

  update public.trading_members
     set user_id = auth.uid()
   where lower(email::text) = lower(auth.email())
     and active
     and (user_id is null or user_id = auth.uid());
  get diagnostics claimed = row_count;
  return claimed = 1;
end;
$$;

revoke all on function public.is_trading_member() from public;
revoke all on function public.claim_trading_membership() from public;
grant execute on function public.is_trading_member() to authenticated;
grant execute on function public.claim_trading_membership() to authenticated;

create policy "members can read themselves"
on public.trading_members for select to authenticated
using (user_id = (select auth.uid()) and active);

create policy "members can read paper updates"
on public.paper_updates for select to authenticated
using ((select public.is_trading_member()));

grant select on public.trading_members to authenticated;
grant select on public.paper_updates to authenticated;

insert into public.trading_members (email, display_name, role)
values ('sb@prishi.in', 'Prishi', 'owner')
on conflict (email) do nothing;

insert into public.paper_updates (
  as_of, recorded_at, status, headline, summary, portfolio, signals, details, source
) values (
  '2026-09-21',
  '2026-09-21T18:04:35.379340+05:30',
  'verified',
  'Seed snapshot verified',
  'No ETF qualified for the first paper session. Capital remained fully in simulated cash.',
  '{"starting_capital":"28000.00","cash":"28000.00","ending_equity":"28000.00","net":"0","open_position":null,"trades":[],"halted_at_loss_limit":false}',
  '{"NIFTYBEES.NS":{"close":"267.76","sma":"277.21574661254882765","previous_high":"283.94000244140625","eligible":false,"reasons":["close_not_above_200_session_average","no_close_above_previous_20_session_high"]},"JUNIORBEES.NS":{"close":"782.31","sma":"754.9882409667968765","previous_high":"821.9000244140625","eligible":false,"reasons":["no_close_above_previous_20_session_high"]}}',
  '{"trial_session":0,"eligible_session":"2026-09-22","data_quality":"verified"}',
  'Frozen paper snapshot'
), (
  '2026-09-22',
  '2026-09-22T17:36:39.283845+05:30',
  'blocked',
  'Data validation blocked decisions',
  'Vendor volumes disagreed with NSE and the refreshed history changed a frozen input representation. No paper decision was generated or backdated.',
  '{"starting_capital":"28000.00","cash":"28000.00","ending_equity":"28000.00","net":"0","open_position":null,"trades":[],"halted_at_loss_limit":false}',
  '{}',
  '{"trial_session":1,"data_quality":"blocked","issues":["NIFTYBEES vendor volume 5394993 vs NSE 5397108","JUNIORBEES vendor volume 232905 vs NSE 232951","21 September source values changed numeric representation"],"snapshot_created":false}',
  'NSE cross-check and frozen-input audit'
)
on conflict (as_of) do nothing;
