create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

do $$
declare
  existing_job record;
begin
  for existing_job in
    select jobid from cron.job where jobname = 'gold-tracker-every-30-minutes'
  loop
    perform cron.unschedule(existing_job.jobid);
  end loop;
end
$$;

select cron.schedule(
  'gold-tracker-every-30-minutes',
  '0,30 3-18 * * 1-6',
  $worker$
    select net.http_post(
      url := 'https://cgnqiyladgdjufarsatn.supabase.co/functions/v1/gold-tracker',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-worker-secret', (
          select secret_value
          from private.worker_secrets
          where worker_name = 'gold-tracker'
        )
      ),
      body := jsonb_build_object('scheduled_at', now()),
      timeout_milliseconds := 120000
    ) as request_id;
  $worker$
);
