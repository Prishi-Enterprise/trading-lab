-- Mark the index entry complete when the immutable final paper snapshot lands.
create function public.complete_nse_experiment()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.experiment_slug = 'etf-breakout-nse-v2' and new.status = 'complete' then
    update public.experiments set status = 'complete' where slug = new.experiment_slug;
  end if;
  return new;
end;
$$;
revoke all on function public.complete_nse_experiment() from public, anon, authenticated;
create trigger complete_nse_experiment
after insert or update of status on public.paper_updates
for each row execute function public.complete_nse_experiment();
