# Prishi Trading Lab frontend

Private Next.js dashboard for the paper-trading experiment. It uses its own Supabase project for six-digit email authentication, an explicit membership list and a read-only paper update feed. It has no brokerage connection and no write controls for trades.

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

The dashboard is designed for Vercel. Required Vercel variables are `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` and `NEXT_PUBLIC_APP_URL`. Configure them for production, preview and development.

## Checks

```sh
npm test
npm run lint
npm run typecheck
npm run build
```

The server queries Supabase at request time. No private paper state, broker credential or service-role key is bundled into the browser.
