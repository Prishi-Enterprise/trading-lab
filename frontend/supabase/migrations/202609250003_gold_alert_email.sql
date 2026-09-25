-- Keep each threshold crossing and its email outcome independent of price snapshots.
create table public.gold_alert_deliveries (
  observed_on date not null,
  metric text not null,
  threshold integer not null,
  label text not null,
  price numeric not null,
  open_price numeric not null,
  change_pct numeric not null,
  triggered_at timestamptz not null,
  status text not null default 'pending' check (status in ('pending', 'sent', 'failed', 'expired')),
  attempts integer not null default 0,
  sent_at timestamptz,
  provider_id text,
  last_error text,
  primary key (observed_on, metric, threshold)
);

create index gold_alert_deliveries_pending_idx
  on public.gold_alert_deliveries (triggered_at)
  where status = 'pending';

alter table public.gold_alert_deliveries enable row level security;
create policy "members can read gold alert delivery status"
on public.gold_alert_deliveries for select to authenticated
using ((select public.is_trading_member()));

grant select on public.gold_alert_deliveries to authenticated;
grant select, insert, update on public.gold_alert_deliveries to service_role;
