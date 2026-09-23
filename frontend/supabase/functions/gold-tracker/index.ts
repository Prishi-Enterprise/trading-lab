type Quote = {
  metric: string;
  label: string;
  price: number;
  asOf: string | null;
};

type GoldMetric = {
  metric: string;
  label: string;
  price: number;
  unit: string;
  as_of: string;
  checked_at: string;
  open_price: number;
  open_at: string;
  change_pct: number;
  alerts_sent: number[];
};

type GoldUpdate = {
  observed_at: string;
  observed_on: string;
  status: "verified" | "partial" | "failed";
  headline: string;
  summary: string;
  metrics: GoldMetric[];
  issues: string[];
  interval_minutes: number;
  source: string;
};

type HistoryRow = Pick<GoldUpdate, "observed_at" | "observed_on" | "metrics" | "source">;

const IST = "Asia/Kolkata";
const SOURCES = {
  bullions: "https://bullions.co.in/location/ahmedabad/",
  suvarnakrupa: "https://www.suvarnakrupa.in/today-gold-rate",
};
const WATCH = [
  ["bullions:gold24k_10g", "Gold 24K /10g (Ahmedabad bullion rate)"],
  ["bullions:mcx_gold_10g", "Gold MCX /10g (live futures)"],
  ["suvarnakrupa:gold24k_10g", "Gold 24K /10g (Suvarnakrupa showroom rate)"],
] as const;
const THRESHOLDS = [-2, 2, -5, 5, -10, 10];
const DEFAULT_INTERVAL = 30;
const MIN_INTERVAL = 30;
const MAX_INTERVAL = 120;
const MIN_LEARNING_SAMPLES = 6;
const MONTHS: Record<string, number> = {
  Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6,
  Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12,
};
const USER_AGENT = "Mozilla/5.0 (compatible; PrishiTradingLab/1.0; +https://trading.prishi.in)";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function localParts(value: Date) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: IST,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    weekday: "short",
  }).formatToParts(value);
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return {
    date: `${get("year")}-${get("month")}-${get("day")}`,
    hour: Number(get("hour")),
    minute: Number(get("minute")),
    weekday: get("weekday"),
  };
}

function activeWindow(now: Date) {
  const local = localParts(now);
  const activeDay = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].includes(local.weekday);
  const minutes = local.hour * 60 + local.minute;
  return activeDay && minutes >= 9 * 60 && minutes <= 23 * 60 + 30;
}

function learnedInterval(rows: HistoryRow[], hour: number) {
  const lastPrice = new Map<string, number>();
  const lastDay = new Map<string, string>();
  let checks = 0;
  let changes = 0;

  for (const row of [...rows].sort((a, b) => a.observed_at.localeCompare(b.observed_at))) {
    const parts = localParts(new Date(row.observed_at));
    for (const metric of row.metrics ?? []) {
      if (!WATCH.some(([watched]) => watched === metric.metric)) continue;
      const priorDay = lastDay.get(metric.metric);
      const priorPrice = lastPrice.get(metric.metric);
      if (priorDay === row.observed_on && parts.hour === hour && priorPrice !== undefined) {
        checks += 1;
        if (metric.price !== priorPrice) changes += 1;
      }
      lastDay.set(metric.metric, row.observed_on);
      lastPrice.set(metric.metric, metric.price);
    }
  }

  if (checks < MIN_LEARNING_SAMPLES) return DEFAULT_INTERVAL;
  const rate = changes / checks;
  if (rate >= 0.6) return MIN_INTERVAL;
  if (rate <= 0.1) return MAX_INTERVAL;
  const interval = MAX_INTERVAL - ((rate - 0.1) / 0.5) * (MAX_INTERVAL - MIN_INTERVAL);
  return Math.round(interval / MIN_INTERVAL) * MIN_INTERVAL;
}

function number(value: string) {
  return Number(value.replaceAll(",", "").replace("₹", "").trim());
}

function istTimestamp(day: string, month: string, year: string, hour: string, minute: string, ampm?: string) {
  let h = Number(hour);
  if (ampm && h <= 12) {
    if (ampm === "PM" && h !== 12) h += 12;
    if (ampm === "AM" && h === 12) h = 0;
  }
  const monthNumber = MONTHS[month];
  if (!monthNumber) return null;
  return `${year}-${String(monthNumber).padStart(2, "0")}-${String(Number(day)).padStart(2, "0")}T${String(h).padStart(2, "0")}:${minute}:00+05:30`;
}

function parseBullions(page: string): Quote[] {
  const quotes: Quote[] = [];
  const updated = page.match(/Last Update<\/i>\s*:\s*<strong>\s*[A-Za-z]+,\s*(\d{1,2}) ([A-Za-z]{3}) (\d{4}) (\d{1,2}):(\d{2})\s*([AP]M)?/);
  const asOf = updated ? istTimestamp(updated[1], updated[2], updated[3], updated[4], updated[5], updated[6]) : null;
  const rows = page.matchAll(/<td[^>]*text-left[^>]*>\s*Gold (\d{2}) Karat.*?<\/td>((?:\s*<td[^>]*>[\d,.]+<\/td>)+)/gs);
  const seen = new Set<string>();
  for (const row of rows) {
    const values = [...row[2].matchAll(/<td[^>]*>([\d,.]+)<\/td>/g)].map((match) => match[1]);
    const key = `gold${row[1]}k_10g`;
    if (values.length >= 2 && !seen.has(key)) {
      seen.add(key);
      quotes.push({ metric: `bullions:${key}`, label: `Gold ${row[1]}K /10g (Ahmedabad bullion rate)`, price: number(values[1]), asOf });
    }
  }
  const mcx = page.match(/Gold - India MCX.*?<\/td>((?:\s*<td[^>]*>\s*<div>[^<]*<\/div>\s*<\/td>){7})/s);
  if (mcx) {
    const values = [...mcx[1].matchAll(/<div>([^<]*)<\/div>/g)].map((match) => match[1]);
    let mcxAsOf = asOf;
    const match = values[6]?.match(/\s*(\d{1,2}) ([A-Za-z]{3}), (\d{1,2}):(\d{2})/);
    if (match) {
      const year = localParts(new Date()).date.slice(0, 4);
      mcxAsOf = istTimestamp(match[1], match[2], year, match[3], match[4]);
    }
    quotes.push({ metric: "bullions:mcx_gold_10g", label: "Gold MCX /10g (live futures)", price: number(values[0]), asOf: mcxAsOf });
  }
  if (!quotes.length) throw new Error("bullions: no prices found (markup changed or access blocked)");
  return quotes;
}

function parseSuvarnakrupa(page: string): Quote[] {
  const updated = page.match(/Rates for\s*<b>(\d{1,2}) ([A-Za-z]{3}) (\d{4})<\/b>.*?Updated\s*<b>(\d{1,2}):(\d{2}) ([AP]M)<\/b>/s);
  const price = page.match(/<span class="c-badge">24K<\/span>\s*<span class="c-sub">999 Fine Gold<\/span>.*?data-count="([\d,.]+)"/s);
  if (!updated || !price) throw new Error("suvarnakrupa: no timestamped 24K price found (markup changed or access blocked)");
  const asOf = istTimestamp(updated[1], updated[2], updated[3], updated[4], updated[5], updated[6]);
  return [{
    metric: "suvarnakrupa:gold24k_10g",
    label: "Gold 24K /10g (Suvarnakrupa showroom rate)",
    price: number(price[1]),
    asOf,
  }];
}

async function fetchSource(name: keyof typeof SOURCES) {
  const response = await fetch(SOURCES[name], {
    headers: { "user-agent": USER_AGENT, accept: "text/html,application/xhtml+xml" },
    signal: AbortSignal.timeout(25_000),
  });
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
  const page = await response.text();
  return name === "bullions" ? parseBullions(page) : parseSuvarnakrupa(page);
}

async function restRequest(url: string, serviceKey: string, init: RequestInit = {}) {
  return fetch(url, {
    ...init,
    headers: {
      apikey: serviceKey,
      authorization: `Bearer ${serviceKey}`,
      "content-type": "application/json",
      ...(init.headers ?? {}),
    },
  });
}

Deno.serve(async (request) => {
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !serviceKey) return json({ error: "Missing Supabase runtime configuration" }, 500);

  const candidate = request.headers.get("x-worker-secret") ?? "";
  const verification = await restRequest(`${supabaseUrl}/rest/v1/rpc/verify_worker_secret`, serviceKey, {
    method: "POST",
    body: JSON.stringify({ requested_worker: "gold-tracker", candidate_secret: candidate }),
  });
  if (!verification.ok || await verification.json() !== true) return json({ error: "Unauthorized" }, 401);

  const now = new Date();
  const local = localParts(now);
  if (!activeWindow(now)) return json({ status: "skipped", reason: "outside active window", observed_on: local.date });

  const historyStart = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
  const historyUrl = new URL(`${supabaseUrl}/rest/v1/gold_updates`);
  historyUrl.searchParams.set("observed_at", `gte.${historyStart}`);
  historyUrl.searchParams.set("select", "observed_at,observed_on,metrics,source");
  historyUrl.searchParams.set("order", "observed_at.asc");
  historyUrl.searchParams.set("limit", "1000");
  const historyResponse = await restRequest(historyUrl.toString(), serviceKey);
  const historyRows = historyResponse.ok ? await historyResponse.json() as HistoryRow[] : [];
  const interval = learnedInterval(historyRows, local.hour);
  const lastCloudObservation = historyRows.findLast((row) =>
    row.source.startsWith("Supabase Edge Function") &&
    WATCH.every(([watched]) => row.metrics.some((metric) => metric.metric === watched))
  );
  if (lastCloudObservation) {
    const elapsedMinutes = (now.getTime() - new Date(lastCloudObservation.observed_at).getTime()) / 60_000;
    if (elapsedMinutes < interval - 1) {
      return json({
        status: "skipped",
        reason: "learned interval has not elapsed",
        learned_interval_minutes: interval,
        observed_on: local.date,
      });
    }
  }

  const priorResponse = await restRequest(
    `${supabaseUrl}/rest/v1/gold_updates?observed_on=eq.${local.date}&select=*&order=observed_at.desc&limit=1`,
    serviceKey,
  );
  const priorRows = priorResponse.ok ? await priorResponse.json() as GoldUpdate[] : [];
  const priorMetrics = new Map((priorRows[0]?.metrics ?? []).map((metric) => [metric.metric, metric]));

  const results = await Promise.allSettled([fetchSource("bullions"), fetchSource("suvarnakrupa")]);
  const issues: string[] = [];
  const quotes = new Map<string, Quote>();
  for (const result of results) {
    if (result.status === "rejected") issues.push(result.reason instanceof Error ? result.reason.message : "source fetch failed");
    else for (const quote of result.value) quotes.set(quote.metric, quote);
  }

  const metrics: GoldMetric[] = [];
  const newAlerts: Array<{ metric: string; thresholds: number[]; change_pct: number }> = [];
  for (const [metric, label] of WATCH) {
    const quote = quotes.get(metric);
    if (!quote) {
      issues.push(`${metric}: not available this run`);
      continue;
    }
    if (!quote.asOf || localParts(new Date(quote.asOf)).date !== local.date) {
      issues.push(`${metric}: source quote is missing a same-day IST timestamp`);
      continue;
    }
    const prior = priorMetrics.get(metric);
    const openPrice = prior?.open_price ?? quote.price;
    const openAt = prior?.open_at ?? new Intl.DateTimeFormat("en-IN", {
      timeZone: IST, hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).format(new Date(quote.asOf)) + " IST";
    const changePct = Math.round(((quote.price - openPrice) / openPrice * 100) * 10_000) / 10_000;
    const sent = new Set(prior?.alerts_sent ?? []);
    const crossed = THRESHOLDS.filter((threshold) => threshold < 0 ? changePct <= threshold : changePct >= threshold);
    const fresh = crossed.filter((threshold) => !sent.has(threshold));
    for (const threshold of fresh) sent.add(threshold);
    if (fresh.length) newAlerts.push({ metric, thresholds: fresh, change_pct: changePct });
    metrics.push({
      metric, label, price: quote.price, unit: "INR / 10g", as_of: quote.asOf,
      checked_at: now.toISOString(), open_price: openPrice, open_at: openAt,
      change_pct: changePct, alerts_sent: [...sent],
    });
  }

  const status: GoldUpdate["status"] = metrics.length === WATCH.length && issues.length === 0
    ? "verified"
    : metrics.length > 0 ? "partial" : "failed";
  const update: GoldUpdate = {
    observed_at: now.toISOString(),
    observed_on: local.date,
    status,
    headline: status === "verified" ? "Gold sources verified" : status === "partial" ? "Gold update partially verified" : "Gold sources unavailable",
    summary: status === "verified"
      ? `Recorded ${metrics.length} watched metrics from same-day public source snapshots.`
      : status === "partial"
        ? `Recorded ${metrics.length} watched metrics, with one or more source or freshness issues.`
        : "No current watched metric could be verified; the previous quote remains historical only.",
    metrics,
    issues: [...new Set(issues)],
    interval_minutes: interval,
    source: "Supabase Edge Function · adaptive Ahmedabad gold tracker",
  };

  const upsert = await restRequest(`${supabaseUrl}/rest/v1/gold_updates?on_conflict=observed_at`, serviceKey, {
    method: "POST",
    headers: { prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify(update),
  });
  if (!upsert.ok) return json({ error: "Could not publish gold update", detail: await upsert.text() }, 500);
  return json({ status, observed_at: update.observed_at, metric_count: metrics.length, issue_count: update.issues.length, new_alerts: newAlerts });
});
