import Link from "next/link";
import { Brand } from "@/components/brand";
import { LabHeader } from "@/components/lab-header";
import { requireTradingMember } from "@/lib/auth";
import { money, type GoldMetric, type GoldUpdate } from "@/lib/dashboard";

export const dynamic = "force-dynamic";

const watchedMetrics = [
  ["bullions:gold24k_10g", "Ahmedabad bullion 24K", "Primary association rate"],
  ["bullions:mcx_gold_10g", "India MCX gold", "Continuously moving futures snapshot"],
  ["aib:retail_999_10g", "Ahmedabad retail 999", "Secondary retail snapshot"],
];

function timestamp(value: string | null | undefined) {
  if (!value) return "No source timestamp";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

function metricById(metrics: GoldMetric[], id: string) {
  return metrics.find((metric) => metric.metric === id);
}

function movement(metric: GoldMetric | undefined) {
  if (!metric || metric.change_pct === null) return "Opening reference pending";
  const sign = metric.change_pct > 0 ? "+" : "";
  return `${sign}${metric.change_pct.toFixed(2)}% vs daily open`;
}

export default async function GoldTrackerPage() {
  const { supabase, user, membership } = await requireTradingMember();
  const { data, error } = await supabase
    .from("gold_updates")
    .select("*")
    .order("observed_at", { ascending: false })
    .limit(12);
  if (error) throw new Error("Could not load the gold tracker record.");

  const updates = (data ?? []) as GoldUpdate[];
  const latest = updates[0];
  const metrics = latest?.metrics ?? [];
  const primary = metricById(metrics, "bullions:gold24k_10g") ?? metrics[0];
  const workerLabel = latest
    ? latest.status === "verified" ? "WORKER VERIFIED" : latest.status === "partial" ? "PARTIAL DATA" : "SOURCE FAILURE"
    : "WORKER NOT CONNECTED";

  return (
    <main className="dashboard-shell commodities-shell">
      <LabHeader active="commodities" displayName={membership.display_name || user.email || "Member"} />

      <section className="tracker-breadcrumb"><Link href="/commodities">Commodities</Link><span>/</span><strong>Gold Price Tracker</strong></section>
      <section className="gold-hero">
        <div className="gold-symbol" aria-hidden="true">Au<small>79</small></div>
        <div><p className="eyebrow">AHMEDABAD · DAILY OPEN COMPARISON</p><h1>Gold Price Tracker</h1><p>Watch price movement across public sources without turning a quote into a trading recommendation.</p></div>
        <span className={`status-chip gold-status ${latest?.status ?? "disconnected"}`}>{workerLabel}</span>
      </section>

      <section className="tracker-metrics" aria-label="Gold tracker status">
        <article><p>Latest observed price</p><strong>{primary ? money(primary.price) : "—"}</strong><span>{primary ? timestamp(primary.as_of ?? primary.checked_at) : "No verified runtime quote"}</span></article>
        <article><p>Polling schedule</p><strong>{latest?.interval_minutes ?? 10} min</strong><span>Codex heartbeat, Mon–Sat · 09:00–23:45 IST</span></article>
        <article><p>Alert tiers</p><strong>±2 · 5 · 10%</strong><span>Once per metric per day</span></article>
        <article><p>Execution</p><strong>Disabled</strong><span>Observation and alerts only</span></article>
      </section>

      {latest && (
        <section className={`status-banner gold-update ${latest.status}`}>
          <div className="status-icon" aria-hidden="true">{latest.status === "verified" ? "✓" : "!"}</div>
          <div><p className="eyebrow">LATEST COLLECTION · {timestamp(latest.observed_at).toUpperCase()}</p><h2>{latest.headline}</h2><p>{latest.summary}</p></div>
          <span className="status-tag">{latest.status.toUpperCase()}</span>
        </section>
      )}

      <section className="content-grid tracker-grid">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">WATCH LIST</p><h2>Three views of Ahmedabad gold.</h2></div><span>₹ / 10g</span></div>
          <div className="watch-list">
            {watchedMetrics.map(([id, name, note]) => {
              const metric = metricById(metrics, id);
              return <div key={id}><span className={`watch-dot ${metric ? "live" : ""}`} /><div><strong>{name}</strong><small>{metric ? movement(metric) : note}</small></div><b>{metric ? money(metric.price) : "—"}</b></div>;
            })}
          </div>
        </article>
        <article className="panel rules-panel">
          <p className="eyebrow">CURRENT OPERATING RULES</p><h2>Transparent by design.</h2>
          <dl><div><dt>City</dt><dd>Ahmedabad</dd></div><div><dt>Active days</dt><dd>Mon–Sat</dd></div><div><dt>Minimum interval</dt><dd>5 minutes</dd></div><div><dt>Default interval</dt><dd>10 minutes</dd></div><div><dt>Quote freshness</dt><dd>Same IST day</dd></div><div><dt>Trading signal</dt><dd>None</dd></div></dl>
        </article>
      </section>

      {latest?.issues?.length > 0 && (
        <section className="panel issue-panel gold-issues">
          <div><p className="eyebrow">COLLECTION ISSUES</p><h2>Unverified sources stay visible.</h2></div>
          <div className="issue-list">{latest.issues.map((issue) => <p key={issue}><span>!</span>{issue}</p>)}</div>
        </section>
      )}

      <section className="panel sources-panel">
        <div><p className="eyebrow">SOURCE DISCIPLINE</p><h2>Public snapshots, with clear limits.</h2></div>
        <div className="source-list">
          <article><span>PRIMARY</span><h3>bullions.co.in</h3><p>Server-rendered Ahmedabad association and MCX tables. Cloudflare changes can interrupt collection.</p></article>
          <article><span>SECONDARY</span><h3>allindiabullion.com</h3><p>Server-rendered retail 999 snapshot. Live ticks use a protected channel and are intentionally excluded.</p></article>
          <article><span>DEFINITION</span><h3>Daily open</h3><p>The first same-day IST quote recorded by the worker. Neither source publishes an official opening price.</p></article>
        </div>
      </section>

      <section className="tracker-note"><strong>Dashboard connection</strong><p>Each completed heartbeat publishes a sanitized collection record to Supabase. Runtime state and notification credentials remain local and ignored.</p><a href="https://github.com/Prishi-Enterprise/trading-lab/tree/main/commodities/gold-price-tracker">View source module ↗</a></section>

      <footer className="dashboard-footer"><Brand inverse /><p>Observation only · No commodity order or advice is generated</p><span>Signed in as {user.email}</span></footer>
    </main>
  );
}
