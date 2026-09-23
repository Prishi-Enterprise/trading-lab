do $$
declare
  existing_job record;
begin
  for existing_job in
    select jobid
    from cron.job
    where jobname in (
      'gold-tracker-every-30-minutes',
      'gold-tracker-half-hour',
      'gold-tracker-on-hour'
    )
  loop
    perform cron.unschedule(existing_job.jobid);
  end loop;
end
$$;

select cron.schedule(
  'gold-tracker-half-hour',
  '30 3-17 * * 1-6',
  $worker$
    select net.http_post(
      url := 'https://cgnqiyladgdjufarsatn.supabase.co/functions/v1/gold-tracker',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-worker-secret', (
          select secret_value from private.worker_secrets where worker_name = 'gold-tracker'
        )
      ),
      body := jsonb_build_object('scheduled_at', now()),
      timeout_milliseconds := 120000
    ) as request_id;
  $worker$
);

select cron.schedule(
  'gold-tracker-on-hour',
  '0 4-18 * * 1-6',
  $worker$
    select net.http_post(
      url := 'https://cgnqiyladgdjufarsatn.supabase.co/functions/v1/gold-tracker',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-worker-secret', (
          select secret_value from private.worker_secrets where worker_name = 'gold-tracker'
        )
      ),
      body := jsonb_build_object('scheduled_at', now()),
      timeout_milliseconds := 120000
    ) as request_id;
  $worker$
);
