create table public.gold_updates (
  observed_at timestamptz primary key,
  observed_on date not null,
  status text not null check (status in ('verified', 'partial', 'failed')),
  headline text not null,
  summary text not null,
  metrics jsonb not null default '[]'::jsonb check (jsonb_typeof(metrics) = 'array'),
  issues jsonb not null default '[]'::jsonb check (jsonb_typeof(issues) = 'array'),
  interval_minutes integer not null check (interval_minutes between 5 and 1440),
  source text not null default 'Ahmedabad gold tracker',
  created_at timestamptz not null default now()
);

alter table public.gold_updates enable row level security;

create policy "members can read gold updates"
on public.gold_updates for select to authenticated
using ((select public.is_trading_member()));

grant select on public.gold_updates to authenticated;
