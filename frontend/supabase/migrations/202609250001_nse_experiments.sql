-- Separate each experiment while preserving the stopped v1 paper record.
create table public.experiments (
  slug text primary key,
  title text not null,
  kind text not null check (kind in ('prospective', 'retrospective')),
  status text not null check (status in ('active', 'stopped', 'complete')),
  category text not null,
  started_on date,
  ends_on date,
  summary text not null,
  method text not null,
  display_order integer not null default 0,
  created_at timestamptz not null default now()
);

insert into public.experiments (slug, title, kind, status, category, started_on, ends_on, summary, method, display_order)
values
  ('etf-breakout-nse-v2', 'NSE-only ETF paper week', 'prospective', 'active', 'Stocks', '2026-09-25', '2026-10-01',
   'Five completed NSE sessions using frozen breakout rules, simulated fills and a ₹28,000 paper portfolio.',
   'Official NSE cash-market bhavcopy only. A signal is frozen after the session and may be filled at the following session open.', 10),
  ('etf-breakout-v1', 'ETF breakout data trial', 'prospective', 'stopped', 'Stocks', '2026-09-22', '2026-09-28',
   'Stopped after conflicting vendor and NSE volumes prevented reliable paper decisions.',
   'The verified seed and blocked review are retained as an audit trail. No return is inferred from missing sessions.', 20),
  ('fixed-rule-strategy-screen', 'Fixed-rule strategy screen', 'retrospective', 'complete', 'Stocks', '2026-09-25', '2026-09-25',
   'Historical SMA crossover and mean-reversion checks on validated NSE ETF bars.',
   'Retrospective screen only. These variants did not become prospective paper strategies.', 30)
on conflict (slug) do nothing;

alter table public.paper_updates
  add column experiment_slug text not null default 'etf-breakout-v1'
  references public.experiments(slug);
alter table public.paper_updates drop constraint paper_updates_pkey;
alter table public.paper_updates add primary key (experiment_slug, as_of);
create index paper_updates_latest_per_experiment
  on public.paper_updates (experiment_slug, as_of desc);

insert into public.paper_updates
  (experiment_slug, as_of, recorded_at, status, headline, summary, portfolio, signals, details, source)
values
  ('fixed-rule-strategy-screen', '2026-09-25', '2026-09-25T13:30:00+05:30', 'complete',
   'No fixed-rule strategy qualified for a prospective trial',
   'Four SMA crossover variants lost money across the full window; the 20-day mean-reversion rule made no trades.',
   '{}'::jsonb, '{}'::jsonb,
   '{"history_start":"2025-08-01","history_end":"2026-09-24","validated_sessions":284,"evaluation_start":"2025-09-17","later_slice_start":"2026-06-16","results":[{"symbol":"NIFTYBEES.NS","rule":"10/20 SMA","net":"-363.49","trades":7,"later_net":"-185.45"},{"symbol":"NIFTYBEES.NS","rule":"10/30 SMA","net":"-344.18","trades":5,"later_net":"-7.28"},{"symbol":"NIFTYBEES.NS","rule":"20-day -10% mean reversion","net":"0.00","trades":0,"later_net":"0.00"},{"symbol":"JUNIORBEES.NS","rule":"10/20 SMA","net":"-555.29","trades":8,"later_net":"64.38"},{"symbol":"JUNIORBEES.NS","rule":"10/30 SMA","net":"-536.95","trades":5,"later_net":"44.58"},{"symbol":"JUNIORBEES.NS","rule":"20-day -10% mean reversion","net":"0.00","trades":0,"later_net":"0.00"}]}'::jsonb,
   'Retrospective screen on validated official NSE ETF bars')
on conflict (experiment_slug, as_of) do nothing;

-- A verified prospective decision is immutable. Blocked attempts can be replaced
-- by a verified record on a same-day retry while the official archive is late.
create function public.guard_frozen_nse_update()
returns trigger language plpgsql set search_path = '' as $$
begin
  if old.experiment_slug = 'etf-breakout-nse-v2' and old.status in ('verified', 'complete') then
    raise exception 'Frozen NSE paper snapshot cannot be changed or deleted';
  end if;
  return coalesce(new, old);
end;
$$;
create trigger guard_frozen_nse_update
before update or delete on public.paper_updates
for each row execute function public.guard_frozen_nse_update();

create table public.nse_daily_bars (
  day date not null,
  symbol text not null check (symbol in ('NIFTYBEES.NS', 'JUNIORBEES.NS')),
  open_price text not null,
  high_price text not null,
  low_price text not null,
  close_price text not null,
  volume bigint not null check (volume >= 0),
  archive_sha256 text not null check (archive_sha256 ~ '^[0-9a-f]{64}$'),
  source_url text not null,
  created_at timestamptz not null default now(),
  primary key (day, symbol)
);

alter table public.experiments enable row level security;
alter table public.nse_daily_bars enable row level security;
create policy "members can read experiments" on public.experiments
  for select to authenticated using ((select public.is_trading_member()));
grant select on public.experiments to authenticated;
-- Historical bar inputs and archive hashes remain service-role only.
revoke all on public.nse_daily_bars from anon, authenticated;

insert into private.worker_secrets (worker_name, secret_value)
values ('nse-paper-week', encode(extensions.gen_random_bytes(32), 'hex'))
on conflict (worker_name) do nothing;

-- These UTC instants are 18:30 and 20:30 IST on each trial day.
-- The last invocation retires both cron jobs instead of leaving an annual heartbeat.
create function private.invoke_nse_paper_week()
returns void language plpgsql security definer set search_path = '' as $$
declare
  local_day date := (now() at time zone 'Asia/Kolkata')::date;
  local_clock time := (now() at time zone 'Asia/Kolkata')::time;
  existing_job record;
begin
  if local_day in ('2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01')
     and local_clock >= time '16:00' then
    perform net.http_post(
      url := 'https://cgnqiyladgdjufarsatn.supabase.co/functions/v1/nse-paper-week',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-worker-secret', (select secret_value from private.worker_secrets where worker_name = 'nse-paper-week')
      ),
      body := jsonb_build_object('scheduled_at', now()),
      timeout_milliseconds := 120000
    );
  end if;
  if local_day > date '2026-10-01' or (local_day = date '2026-10-01' and local_clock >= time '20:30') then
    for existing_job in select jobid from cron.job where jobname in ('nse-paper-week-2026', 'nse-paper-week-final-2026')
    loop perform cron.unschedule(existing_job.jobid); end loop;
  end if;
end;
$$;
revoke all on function private.invoke_nse_paper_week() from public, anon, authenticated;

do $$
declare existing_job record;
begin
  for existing_job in select jobid from cron.job where jobname in ('nse-paper-week-2026', 'nse-paper-week-final-2026')
  loop perform cron.unschedule(existing_job.jobid); end loop;
end $$;
select cron.schedule(
  'nse-paper-week-2026',
  '0 13,15 25,28,29,30 9 *',
  'select private.invoke_nse_paper_week();'
);
-- October 1 is a separate month; the worker rejects all other dates.
select cron.schedule(
  'nse-paper-week-final-2026',
  '0 13,15 1 10 *',
  'select private.invoke_nse_paper_week();'
);
