# Source research (18 Sep 2026)

## bullions.co.in — `https://bullions.co.in/location/ahmedabad/`  ✅ primary
- WordPress, server-rendered HTML behind Cloudflare. Plain GET with a browser User-Agent returns
  the full page (~390 KB). No API/XHR for the prices.
- **Gold table** (`<table class="data">` after "Gold Rate Today in Ahmedabad"): 24/22/20/18/16/14/12/10K
  per 1 g, 10 g, 100 g, 1 kg, 1 oz, 1 tola. Timestamp in
  `Last Update : <strong>Friday, 18 Sep 2026 10:40 AM`. Quirk: evening values print 24h time with
  "PM" (`21:05 PM`) — parser handles it.
- **Live Exchange Rates** table: Gold/Silver India MCX (₹/10 g, ₹/kg) and US Comex with
  Price, Change, Change%, **High, Low, Previous close**, Last update (`18 Sep, 10:40`, no year).
- Association rate "published once or more during the day"; MCX updates every few minutes.
- Snapshot at research time: 24K ₹1,54,030/10 g; MCX ₹1,53,440 (H 1,53,488 / L 1,52,171 / prev 1,52,981).

## allindiabullion.com — `https://allindiabullion.com/gold-rate/gujarat/ahmedabad`  ⚠️ secondary
- Astro + React islands, Cloudflare (bot-management JS challenge present).
- Server-rendered HTML includes a snapshot of product cards: Gold RETAIL 995 / RTGS 995 /
  995 WITH GST / RETAIL 999 / RTGS 999 / 999 WITH GST, silver equivalents, spot GLD $/₹, and
  `<time dateTime="2026-09-18T05:09:14.605Z">`. That's what we parse.
- Live ticks: browser calls `POST /api/token` (403 without the CF challenge cookie) and
  `POST /api/session`, then a live channel. Not used — fragile and bot-protected.
- Snapshot at research time: 24K ₹1,51,200/10 g, RETAIL 999 ₹1,51,049, RTGS 999 ₹1,53,585.

## No explicit "opening price"
Neither site publishes an open. We define open = first quote of the IST day whose site timestamp
is today (`tracker.py`). For MCX you could alternatively compare to `prev_close` (stored in
`Quote.extra`).

## Realism of thresholds
Daily gold moves are usually < 1–2 %; 5 % days are rare, 10 % is almost unheard of. So ±2 % is the
tier that will actually fire occasionally.

## If blocked
1. Check from a normal Mac terminal (agent sandboxes often block these hosts).
2. If Cloudflare starts serving a challenge to scripts: lower frequency, then consider a headless
   browser (Playwright) fetch just for that source, or switch the watch list to the other site.
3. Other public Ahmedabad sources to evaluate: IBJA rates (ibjarates.com), MCX via broker APIs.

## Change log
- 2026-09-18: initial parsers + fixtures captured.
