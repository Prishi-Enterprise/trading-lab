// Frozen NSE-only prospective paper experiment. No brokerage API or order path.
import Decimal from "npm:decimal.js@10.6.0";
import { unzipSync } from "npm:fflate@0.8.2";

Decimal.set({ precision: 28, rounding: Decimal.ROUND_HALF_UP });
type Bar = { day: string; symbol: string; open_price: string; high_price: string; low_price: string; close_price: string; volume: number; archive_sha256: string; source_url: string };
type Plan = { signal_day: string; close: string; sma: string; previous_high: string; atr: string; average_turnover: string; eligible: boolean; reasons: string[]; entry_cap: string; initial_stop: string; quantity: number; breakout_strength: string };
type Position = { symbol: string; quantity: number; entry_price: string; entry_value: string; entry_fee: string; entry_day: string; signal_day: string; stop: string; highest_close: string; exit_next_open: boolean; sessions: number };
type State = { starting_capital: string; cash: string; ending_equity: string; net: string; open_position: Position | null; trades: Record<string, unknown>[]; halted_at_loss_limit: boolean; total_fees: string; peak_equity: string; max_daily_liquidation_drawdown: string; adverse_bar_drawdown_vs_prior_close_peak: string; exposed_sessions: number; completed_sessions: number };
type Update = { experiment_slug: string; as_of: string; recorded_at: string; status: "verified" | "blocked" | "complete"; headline: string; summary: string; portfolio: State | Record<string, never>; signals: Record<string, Plan>; details: Record<string, unknown>; source: string };

const EXPERIMENT = "etf-breakout-nse-v2";
const CONFIG_SHA256 = "04a48e12f4efc4c40d3ea6c99625217fa2767b04ce82a67aa24b28a6c09547e3";
const CFG = Object.freeze({ paper_capital: "28000.00", max_position_value: "10000.00", planned_risk_per_trade: "250.00", total_loss_limit: "5000.00", trend_sessions: 200, breakout_sessions: 20, atr_sessions: 14, stop_atr_multiple: "2", max_holding_sessions: 60, entry_cap_bps: 30, slippage_bps: 10, minimum_average_turnover: "10000000", trial_start: "2026-09-25", first_possible_execution: "2026-09-28", trial_end: "2026-10-01" });
const DAYS = ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"];
const SYMBOLS = ["JUNIORBEES.NS", "NIFTYBEES.NS"];
const HOLIDAYS = new Set(["2025-08-15", "2025-08-27", "2025-10-02", "2025-10-22", "2025-11-05", "2025-12-25", "2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31", "2026-04-03", "2026-04-14", "2026-05-01", "2026-05-28", "2026-06-26", "2026-09-14", "2026-10-02"]);
const SPECIAL = new Set(["2026-02-01"]);
const D = (value: Decimal.Value) => new Decimal(value);
const min = (...v: Decimal[]) => Decimal.min(...v);
const max = (...v: Decimal[]) => Decimal.max(...v);
const cents = (v: Decimal.Value, rounding = Decimal.ROUND_HALF_UP) => D(v).toDecimalPlaces(2, rounding);
const str = (v: Decimal.Value) => D(v).toString();
const money = (v: Decimal.Value, rounding = Decimal.ROUND_HALF_UP) => cents(v, rounding).toFixed(2);
const cashState = (): State => ({ starting_capital: CFG.paper_capital, cash: CFG.paper_capital, ending_equity: CFG.paper_capital, net: "0.00", open_position: null, trades: [], halted_at_loss_limit: false, total_fees: "0.00", peak_equity: CFG.paper_capital, max_daily_liquidation_drawdown: "0.00", adverse_bar_drawdown_vs_prior_close_peak: "0.00", exposed_sessions: 0, completed_sessions: 0 });
const respond = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json; charset=utf-8" } });

function istNow(now: Date) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(now);
  const get = (name: string) => parts.find((part) => part.type === name)?.value ?? "";
  return { day: `${get("year")}-${get("month")}-${get("day")}`, hour: Number(get("hour")), minute: Number(get("minute")) };
}

async function sha256(bytes: Uint8Array) {
  const hash = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

// Python json.dumps(..., sort_keys=True) encoding used by the frozen local recorder.
function pythonJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(pythonJson).join(", ")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${JSON.stringify(k)}: ${pythonJson(v)}`).join(", ")}}`;
  return JSON.stringify(value);
}

async function prefixHash(bars: Bar[], through: string) {
  const rows: Record<string, (string | number)[][]> = {};
  for (const symbol of SYMBOLS) rows[symbol] = bars.filter((bar) => bar.symbol === symbol && bar.day >= "2025-01-01" && bar.day <= through)
    .map((bar) => [bar.day, bar.open_price, bar.high_price, bar.low_price, bar.close_price, bar.volume]);
  return sha256(new TextEncoder().encode(pythonJson(rows)));
}

function parseCsv(csv: string) {
  const rows: string[][] = [];
  let row: string[] = [], field = "", quoted = false;
  for (let i = 0; i < csv.length; i++) {
    const c = csv[i];
    if (c === '"') { if (quoted && csv[i + 1] === '"') { field += '"'; i++; } else quoted = !quoted; }
    else if (c === "," && !quoted) { row.push(field); field = ""; }
    else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && csv[i + 1] === "\n") i++;
      row.push(field); field = "";
      if (row.some(Boolean)) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function validateBars(bars: Bar[], through: string) {
  const days = [...new Set(bars.map((bar) => bar.day))].sort();
  if (days.length < 200 || days.at(-1) !== through) throw new Error(`Need 200 official shared sessions through ${through}; found ${days.length}`);
  for (const day of days) {
    const matches = bars.filter((bar) => bar.day === day);
    if (matches.length !== 2 || new Set(matches.map((bar) => bar.symbol)).size !== 2 || new Set(matches.map((bar) => bar.archive_sha256)).size !== 1) throw new Error(`Missing or duplicate ETF rows on ${day}`);
  }
  for (let stamp = Date.parse(`${days[0]}T00:00:00Z`); stamp <= Date.parse(`${through}T00:00:00Z`); stamp += 86_400_000) {
    const day = new Date(stamp).toISOString().slice(0, 10);
    const dow = new Date(stamp).getUTCDay();
    if (((dow > 0 && dow < 6 && !HOLIDAYS.has(day)) || SPECIAL.has(day)) && !days.includes(day)) throw new Error(`Missing NSE archive for expected trading day ${day}`);
  }
  for (const symbol of SYMBOLS) {
    const series = bars.filter((bar) => bar.symbol === symbol);
    for (let i = 0; i < series.length; i++) {
      const bar = series[i], o = D(bar.open_price), h = D(bar.high_price), l = D(bar.low_price), c = D(bar.close_price);
      if (![o, h, l, c].every((v) => v.isFinite() && v.gt(0)) || l.gt(min(o, c)) || h.lt(max(o, c)) || l.gt(h) || !Number.isSafeInteger(bar.volume) || bar.volume < 0) throw new Error(`Invalid ETF bar ${symbol} ${bar.day}`);
      if (i > 0 && c.div(series[i - 1].close_price).minus(1).abs().gt("0.20")) throw new Error(`Possible corporate action in ${symbol} on ${bar.day}`);
    }
  }
}

function indicators(series: Bar[], cfg = CFG) {
  const i = series.length - 1;
  if (i < Math.max(cfg.trend_sessions - 1, cfg.breakout_sessions, cfg.atr_sessions)) return null;
  const sma = series.slice(i - cfg.trend_sessions + 1).reduce((a, b) => a.plus(b.close_price), D(0)).div(cfg.trend_sessions);
  const previousHighText = series.slice(i - cfg.breakout_sessions, i).reduce((highest, bar) => D(bar.high_price).gt(highest) ? bar.high_price : highest, series[i - cfg.breakout_sessions].high_price);
  const previousHigh = D(previousHighText);
  const trueRanges = series.slice(i - cfg.atr_sessions + 1).map((bar, j) => {
    const prev = series[i - cfg.atr_sessions + j];
    return max(D(bar.high_price).minus(bar.low_price), D(bar.high_price).minus(prev.close_price).abs(), D(bar.low_price).minus(prev.close_price).abs());
  });
  const atr = trueRanges.reduce((a, b) => a.plus(b), D(0)).div(cfg.atr_sessions);
  const turnover = series.slice(i - cfg.breakout_sessions + 1).reduce((a, b) => a.plus(D(b.close_price).times(b.volume)), D(0)).div(cfg.breakout_sessions);
  return { sma, previousHigh, previousHighText, atr, turnover };
}

function fees(value: Decimal, side: "buy" | "sell", sameDay = false) {
  const brokerage = min(value.times("0.025"), max(D(5), min(D(20), value.times("0.001"))));
  const exchange = value.times("0.0000297"), sebi = value.times("0.000001"), ipft = value.times("0.000001");
  const dp = side === "sell" ? D(20) : D(0);
  const gst = brokerage.plus(exchange).plus(sebi).plus(ipft).plus(dp).times("0.18");
  const stamp = side === "buy" ? value.times("0.00015") : D(0);
  const stt = side === "sell" ? value.times(sameDay ? "0.00025" : "0.00001") : D(0);
  return cents(brokerage.plus(exchange).plus(sebi).plus(ipft).plus(dp).plus(gst).plus(stamp).plus(stt), Decimal.ROUND_UP);
}

function sizePlan(cap: Decimal, stop: Decimal, cash: Decimal) {
  if (stop.lte(0) || stop.gte(cap)) return 0;
  const budget = min(cash, D(CFG.max_position_value));
  const stopFill = cents(stop.times(D(1).minus(D(CFG.slippage_bps).div(10000))));
  let qty = budget.div(cap).floor().toNumber();
  while (qty > 0) {
    const value = cap.times(qty);
    const plannedLoss = cap.minus(stopFill).times(qty).plus(fees(value, "buy")).plus(fees(stopFill.times(qty), "sell"));
    if (value.plus(fees(value, "buy")).lte(cash) && plannedLoss.lte(CFG.planned_risk_per_trade)) return qty;
    qty--;
  }
  return 0;
}

function candidate(series: Bar[], cash: Decimal): Plan {
  const ind = indicators(series);
  if (!ind) throw new Error("Insufficient indicator history");
  const bar = series.at(-1)!;
  const close = D(bar.close_price), reasons: string[] = [];
  if (close.lte(ind.sma)) reasons.push("close_not_above_200_session_average");
  if (close.lte(ind.previousHigh)) reasons.push("no_close_above_previous_20_session_high");
  if (ind.turnover.lt(CFG.minimum_average_turnover)) reasons.push("insufficient_average_turnover");
  const stop = cents(close.minus(D(CFG.stop_atr_multiple).times(ind.atr)));
  const cap = cents(close.times(D(1).plus(D(CFG.entry_cap_bps).div(10000))), Decimal.ROUND_DOWN);
  const quantity = sizePlan(cap, stop, cash);
  if (!quantity) reasons.push("no_size_within_cash_and_risk_limits");
  return { signal_day: bar.day, close: money(close), sma: str(ind.sma), previous_high: ind.previousHighText, atr: str(ind.atr), average_turnover: str(ind.turnover), eligible: reasons.length === 0, reasons, entry_cap: money(cap), initial_stop: money(stop), quantity, breakout_strength: str(close.div(ind.previousHigh).minus(1)) };
}

function nextState(prior: State, frozen: Record<string, Plan>, today: Record<string, Bar>, history: Bar[], day: string): State {
  let cash = D(prior.cash), feesTotal = D(prior.total_fees), position = prior.open_position ? { ...prior.open_position } : null;
  const trades = [...prior.trades], slip = D(CFG.slippage_bps).div(10000);
  let halted = prior.halted_at_loss_limit, exited = false, hadPosition = !!position;
  function closePosition(price: Decimal, reason: string) {
    if (!position) throw new Error("No open paper position");
    const fill = cents(price.times(D(1).minus(slip))), value = fill.times(position.quantity);
    const exitFee = fees(value, "sell", day === position.entry_day);
    cash = cash.plus(value).minus(exitFee); feesTotal = feesTotal.plus(exitFee);
    trades.push({ symbol: position.symbol, signal_day: position.signal_day, entry_day: position.entry_day, exit_day: day,
      entry_price: position.entry_price, exit_price: money(fill), quantity: position.quantity, reason, holding_sessions: position.sessions,
      fees: money(D(position.entry_fee).plus(exitFee)), net: money(value.minus(exitFee).minus(position.entry_value).minus(position.entry_fee)) });
    position = null; exited = true;
  }
  if (position) {
    const bar = today[position.symbol];
    if (!bar) throw new Error(`Missing ${position.symbol} bar on ${day}`);
    position.sessions += 1;
    if (D(bar.open_price).lte(position.stop)) closePosition(D(bar.open_price), "gap_below_stop");
    else if (position.exit_next_open) closePosition(D(bar.open_price), "trend_or_time_exit");
    else if (D(bar.low_price).lte(position.stop)) closePosition(D(position.stop), "stop");
  }
  if (!position && !exited && !halted) {
    if (!frozen || SYMBOLS.some((symbol) => !frozen[symbol])) throw new Error("Missing pre-recorded decision; no past signal can be invented");
    const plans = SYMBOLS.map((symbol) => {
      const plan = frozen[symbol], cap = D(plan.entry_cap), stop = D(plan.initial_stop);
      return { symbol, plan, quantity: Math.min(plan.quantity, sizePlan(cap, stop, cash)) };
    }).filter(({ plan, quantity }) => plan.eligible && quantity > 0)
      .sort((a, b) => D(b.plan.breakout_strength).comparedTo(a.plan.breakout_strength) || b.symbol.localeCompare(a.symbol));
    if (plans.length) {
      const { symbol, plan, quantity } = plans[0], bar = today[symbol];
      const fill = cents(D(bar.open_price).times(D(1).plus(slip)), Decimal.ROUND_UP);
      if (D(plan.initial_stop).lt(bar.open_price) && fill.lte(plan.entry_cap)) {
        const value = fill.times(quantity), entryFee = fees(value, "buy");
        cash = cash.minus(value).minus(entryFee); feesTotal = feesTotal.plus(entryFee);
        position = { symbol, quantity, entry_price: money(fill), entry_value: money(value), entry_fee: money(entryFee), entry_day: day,
          signal_day: plan.signal_day, stop: plan.initial_stop, highest_close: money(fill), exit_next_open: false, sessions: 1 };
        hadPosition = true;
        if (D(bar.low_price).lte(position.stop)) closePosition(D(position.stop), "entry_day_stop");
      }
    }
  }
  let equity = cash, adverse = cash;
  if (position) {
    const bar = today[position.symbol];
    const closeValue = cents(D(bar.close_price).times(D(1).minus(slip))).times(position.quantity);
    const lowValue = cents(D(bar.low_price).times(D(1).minus(slip))).times(position.quantity);
    equity = equity.plus(closeValue).minus(fees(closeValue, "sell"));
    adverse = adverse.plus(lowValue).minus(fees(lowValue, "sell"));
    if (D(CFG.paper_capital).minus(adverse).gte(CFG.total_loss_limit)) { halted = true; position.exit_next_open = true; }
    const ind = indicators(history.filter((b) => b.symbol === position!.symbol));
    position.highest_close = str(max(D(position.highest_close), D(bar.close_price)));
    if (ind) {
      position.stop = money(max(D(position.stop), cents(D(position.highest_close).minus(D(CFG.stop_atr_multiple).times(ind.atr)))));
      position.exit_next_open ||= D(bar.close_price).lt(ind.sma) || position.sessions >= CFG.max_holding_sessions;
    }
  }
  if (D(CFG.paper_capital).minus(equity).gte(CFG.total_loss_limit)) { halted = true; if (position) position.exit_next_open = true; }
  const priorPeak = D(prior.peak_equity);
  return { starting_capital: CFG.paper_capital, cash: money(cash), ending_equity: money(equity), net: money(equity.minus(CFG.paper_capital)),
    open_position: position, trades, halted_at_loss_limit: halted, total_fees: money(feesTotal), peak_equity: money(max(priorPeak, equity)),
    max_daily_liquidation_drawdown: money(max(D(prior.max_daily_liquidation_drawdown), priorPeak.minus(equity))),
    adverse_bar_drawdown_vs_prior_close_peak: money(max(D(prior.adverse_bar_drawdown_vs_prior_close_peak), priorPeak.minus(adverse))),
    exposed_sessions: prior.exposed_sessions + Number(hadPosition), completed_sessions: prior.completed_sessions + 1 };
}

function archiveUrl(day: string) { return `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_${day.replaceAll("-", "")}_F_0000.csv.zip`; }

async function fetchOfficial(day: string) {
  const url = archiveUrl(day);
  const response = await fetch(url, { headers: { "user-agent": "Mozilla/5.0", accept: "application/zip,*/*" }, signal: AbortSignal.timeout(30_000) });
  if (response.status === 404) throw new Error(`Completed NSE archive is not available yet for ${day}`);
  if (!response.ok) throw new Error(`NSE archive HTTP ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  const hash = await sha256(bytes), entries = unzipSync(bytes);
  const csvNames = Object.keys(entries).filter((name) => name.toLowerCase().endsWith(".csv"));
  if (csvNames.length !== 1) throw new Error(`Unexpected NSE archive for ${day}`);
  const rows = parseCsv(new TextDecoder("utf-8").decode(entries[csvNames[0]]).replace(/^\uFEFF/, ""));
  const header = rows.shift() ?? [], col = (name: string) => { const i = header.indexOf(name); if (i < 0) throw new Error(`NSE column ${name} missing`); return i; };
  const fields = Object.fromEntries(["TckrSymb", "SctySrs", "TradDt", "OpnPric", "HghPric", "LwPric", "ClsPric", "TtlTradgVol"].map((name) => [name, col(name)]));
  const chosen = rows.filter((row) => ["NIFTYBEES", "JUNIORBEES"].includes(row[fields.TckrSymb]) && row[fields.SctySrs] === "EQ");
  if (chosen.length !== 2 || new Set(chosen.map((row) => row[fields.TckrSymb])).size !== 2) throw new Error(`Missing or duplicate ETF row on ${day}`);
  const bars = chosen.map((row): Bar => {
    if (row[fields.TradDt] !== day) throw new Error(`Mismatched archive date for ${day}`);
    const price = (field: string) => { const value = row[fields[field]]?.trim(); if (!value || !D(value).isFinite()) throw new Error(`Invalid ${field} on ${day}`); return value; };
    const volume = Number(row[fields.TtlTradgVol]);
    return { day, symbol: `${row[fields.TckrSymb]}.NS`, open_price: price("OpnPric"), high_price: price("HghPric"), low_price: price("LwPric"), close_price: price("ClsPric"), volume, archive_sha256: hash, source_url: url };
  });
  return { bars, hash, url };
}

async function rest(url: string, key: string, init: RequestInit = {}) {
  return fetch(url, { ...init, headers: { apikey: key, authorization: `Bearer ${key}`, "content-type": "application/json", ...(init.headers ?? {}) } });
}

async function readRows<T>(base: string, key: string, table: string, params: Record<string, string>): Promise<T[]> {
  const url = new URL(`${base}/rest/v1/${table}`);
  for (const [name, value] of Object.entries(params)) url.searchParams.set(name, value);
  const response = await rest(url.toString(), key);
  if (!response.ok) throw new Error(`${table} read HTTP ${response.status}: ${(await response.text()).slice(0, 250)}`);
  return response.json();
}

async function upsert(base: string, key: string, table: string, conflict: string, rows: unknown, ignore = false) {
  const response = await rest(`${base}/rest/v1/${table}?on_conflict=${conflict}`, key, { method: "POST", headers: { Prefer: `resolution=${ignore ? "ignore" : "merge"}-duplicates,return=minimal` }, body: JSON.stringify(rows) });
  if (!response.ok) throw new Error(`${table} write HTTP ${response.status}: ${(await response.text()).slice(0, 300)}`);
}

Deno.serve(async (request) => {
  const base = Deno.env.get("SUPABASE_URL"), key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!base || !key) return respond({ error: "Missing Supabase runtime configuration" }, 500);
  const verification = await rest(`${base}/rest/v1/rpc/verify_worker_secret`, key, { method: "POST", body: JSON.stringify({ requested_worker: "nse-paper-week", candidate_secret: request.headers.get("x-worker-secret") ?? "" }) });
  if (!verification.ok || await verification.json() !== true) return respond({ error: "Unauthorized" }, 401);
  const now = new Date(), local = istNow(now), day = local.day;
  if (!DAYS.includes(day) || local.hour < 16) return respond({ status: "skipped", reason: "outside completed trial session", day });
  try {
    const existing = await readRows<Update>(base, key, "paper_updates", { experiment_slug: `eq.${EXPERIMENT}`, as_of: `eq.${day}`, select: "*", limit: "1" });
    if (existing[0] && existing[0].status !== "blocked") return respond({ status: "skipped", reason: "snapshot already frozen", day });
    const index = DAYS.indexOf(day);
    const previous = index ? await readRows<Update>(base, key, "paper_updates", { experiment_slug: `eq.${EXPERIMENT}`, as_of: `eq.${DAYS[index - 1]}`, select: "*", limit: "1" }) : [];
    if (index && (!previous[0] || previous[0].status === "blocked")) throw new Error(`Missing frozen decision from ${DAYS[index - 1]}`);
    const official = await fetchOfficial(day);
    const history = await readRows<Bar>(base, key, "nse_daily_bars", { select: "*", order: "day.asc,symbol.asc", limit: "1000" });
    const conflicting = history.filter((bar) => bar.day === day);
    if (conflicting.length && (conflicting.length !== 2 || conflicting.some((bar) => bar.archive_sha256 !== official.hash))) throw new Error(`Today's NSE archive changed after first fetch`);
    const bars = [...history.filter((bar) => bar.day < day), ...official.bars].sort((a, b) => a.day.localeCompare(b.day) || a.symbol.localeCompare(b.symbol));
    validateBars(bars, day);
    const priorUpdates = await readRows<Update>(base, key, "paper_updates", { experiment_slug: `eq.${EXPERIMENT}`, as_of: `lt.${day}`, select: "*", order: "as_of.asc", limit: "10" });
    for (const prior of priorUpdates.filter((item) => item.status !== "blocked")) {
      if (prior.details.config_sha256 !== CONFIG_SHA256 || prior.details.price_history_sha256 !== await prefixHash(bars, prior.as_of)) throw new Error(`Frozen input changed on ${prior.as_of}; human review required`);
    }
    if (index && priorUpdates.filter((item) => item.status !== "blocked").length !== index) throw new Error("Earlier trial snapshot missing");
    const prior = previous[0], state = index ? nextState(prior.portfolio as State, prior.signals, Object.fromEntries(official.bars.map((bar) => [bar.symbol, bar])), bars, day) : cashState();
    const signals: Record<string, Plan> = {};
    for (const symbol of SYMBOLS) {
      const plan = candidate(bars.filter((bar) => bar.symbol === symbol), D(state.cash));
      if (state.open_position || state.halted_at_loss_limit || day === CFG.trial_end) { plan.eligible = false; plan.reasons.push("existing_position_or_risk_halt_or_trial_complete"); }
      signals[symbol] = plan;
    }
    const eligible = SYMBOLS.filter((symbol) => signals[symbol].eligible);
    const update: Update = { experiment_slug: EXPERIMENT, as_of: day, recorded_at: now.toISOString(), status: day === CFG.trial_end ? "complete" : "verified",
      headline: day === CFG.trial_end ? "NSE paper week complete" : eligible.length ? `${eligible.length} ETF paper setup${eligible.length > 1 ? "s" : ""} recorded` : "No ETF met the frozen paper rules",
      summary: `Official NSE close validated. ${eligible.length ? `Next-session paper setup: ${eligible.join(", ")}.` : "No new paper entry qualified."} Paper equity ${money(state.ending_equity)}; no live order placed.`,
      portfolio: state, signals, source: "Supabase Edge Function · official NSE bhavcopy",
      details: { config_sha256: CONFIG_SHA256, price_history_sha256: await prefixHash(bars, day), source_archive_sha256: official.hash, source_url: official.url,
        validated_sessions: new Set(bars.map((bar) => bar.day)).size, first_possible_execution: CFG.first_possible_execution,
        execution_model: "Next NSE daily open with cap, slippage and estimated fees; simulated only", trial_complete: day === CFG.trial_end } };
    await upsert(base, key, "nse_daily_bars", "day,symbol", official.bars, true);
    await upsert(base, key, "paper_updates", "experiment_slug,as_of", update);
    return respond({ status: "recorded", day, paper_equity: state.ending_equity, paper_net: state.net, eligible_symbols: eligible, archive_sha256: official.hash });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const blocked: Update = { experiment_slug: EXPERIMENT, as_of: day, recorded_at: now.toISOString(), status: "blocked", headline: "NSE paper check blocked",
      summary: `No paper decision was created: ${message}`, portfolio: {}, signals: {}, source: "Supabase Edge Function · official NSE bhavcopy", details: { issues: [message], snapshot_created: false, config_sha256: CONFIG_SHA256 } };
    try { await upsert(base, key, "paper_updates", "experiment_slug,as_of", blocked); }
    catch (writeError) { return respond({ status: "blocked", day, error: message, record_error: String(writeError) }, 500); }
    return respond({ status: "blocked", day, error: message }, 503);
  }
});
