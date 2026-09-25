# Prishi Trading Lab frontend

Private Next.js dashboard for Trading Lab experiments. It uses its own Supabase project for six-digit email authentication, an explicit membership list and read-only experiment feeds. It has no brokerage connection and no write controls for trades.

## Local setup

```sh
cp .env.example .env.local
npm install
npm run dev
```

Set the public URL and publishable key from the dedicated Supabase project. The email template must show the six-digit `{{ .Token }}` value, as in Festivals. The migration seeds `sb@prishi.in` as the initial owner; add other intended viewers to `trading_members` after applying it.

Apply `supabase/migrations/202609230001_initial.sql` to the Trading Lab Supabase project. The migration creates:

- `trading_members`, with one-time membership claiming tied to the authenticated email;
- `paper_updates`, the read-only stock paper-trading feed;
- `gold_updates`, the authenticated Ahmedabad gold collection feed;
- row-level policies that allow active Trading Lab members to read the dashboard;
- the verified 21 September seed and the blocked 22 September review.

Apply later migrations in filename order. `202609250001_nse_experiments.sql` creates a member-only experiment index, gives `paper_updates` a composite experiment/date key, preserves stopped v1 records, protects frozen v2 snapshots, and schedules the NSE worker. `202609250002_complete_nse_experiment.sql` marks the index entry complete when the final snapshot lands. Generate the first-seen official history bootstrap from the repository root with `python3 -m scripts.bootstrap_nse_supabase`; apply the ignored `state/nse-only/bootstrap.sql` **after** the first migration. It seeds 284 validated shared sessions through 24 September 2026 without committing raw bars. Deploy `supabase/functions/nse-paper-week/index.ts` with legacy JWT verification off; its `x-worker-secret` is checked against the service-role-only `private.worker_secrets` table. The worker is scheduled only for the five completed trial days and its last check retires the schedule.

The dashboard is designed for Vercel. Required Vercel variables are `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` and `NEXT_PUBLIC_APP_URL`. Configure them for production, preview and development.

## Checks

```sh
npm test
npm run lint
npm run typecheck
npm run build
```

The server queries Supabase at request time and open experiment pages refresh every minute. No private paper state, broker credential or service-role key is bundled into the browser.
