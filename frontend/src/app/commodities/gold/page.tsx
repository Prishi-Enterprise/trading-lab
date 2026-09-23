import Link from "next/link";
import { Brand } from "@/components/brand";
import { LabHeader } from "@/components/lab-header";
import { requireTradingMember } from "@/lib/auth";

export const dynamic = "force-dynamic";

const watchedMetrics = [
  ["Ahmedabad bullion 24K", "Gold / 10g", "Primary association rate"],
  ["India MCX gold", "Gold / 10g", "Continuously moving futures snapshot"],
  ["Ahmedabad retail 999", "Gold / 10g", "Secondary retail snapshot"],
];

export default async function GoldTrackerPage() {
  const { user, membership } = await requireTradingMember();

  return (
    <main className="dashboard-shell commodities-shell">
      <LabHeader active="commodities" displayName={membership.display_name || user.email || "Member"} />

      <section className="tracker-breadcrumb"><Link href="/commodities">Commodities</Link><span>/</span><strong>Gold Price Tracker</strong></section>
      <section className="gold-hero">
        <div className="gold-symbol" aria-hidden="true">Au<small>79</small></div>
        <div><p className="eyebrow">AHMEDABAD · DAILY OPEN COMPARISON</p><h1>Gold Price Tracker</h1><p>Watch price movement across public sources without turning a quote into a trading recommendation.</p></div>
        <span className="status-chip amber">WORKER NOT CONNECTED</span>
      </section>

      <section className="tracker-metrics" aria-label="Gold tracker status">
        <article><p>Latest observed price</p><strong>—</strong><span>No deployed runtime quote</span></article>
        <article><p>Polling schedule</p><strong>10 min</strong><span>Local worker, 09:00–23:45 IST</span></article>
        <article><p>Alert tiers</p><strong>±2 · 5 · 10%</strong><span>Once per metric per day</span></article>
        <article><p>Execution</p><strong>Disabled</strong><span>Observation and alerts only</span></article>
      </section>

      <section className="content-grid tracker-grid">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">WATCH LIST</p><h2>Three views of Ahmedabad gold.</h2></div><span>₹ / 10g</span></div>
          <div className="watch-list">
            {watchedMetrics.map(([name, unit, note]) => <div key={name}><span className="watch-dot" /><div><strong>{name}</strong><small>{note}</small></div><b>{unit}</b></div>)}
          </div>
        </article>
        <article className="panel rules-panel">
          <p className="eyebrow">CURRENT OPERATING RULES</p><h2>Transparent by design.</h2>
          <dl><div><dt>City</dt><dd>Ahmedabad</dd></div><div><dt>Active days</dt><dd>Mon–Sat</dd></div><div><dt>Minimum interval</dt><dd>5 minutes</dd></div><div><dt>Default interval</dt><dd>10 minutes</dd></div><div><dt>Quote freshness</dt><dd>Same IST day</dd></div><div><dt>Trading signal</dt><dd>None</dd></div></dl>
        </article>
      </section>

      <section className="panel sources-panel">
        <div><p className="eyebrow">SOURCE DISCIPLINE</p><h2>Public snapshots, with clear limits.</h2></div>
        <div className="source-list">
          <article><span>PRIMARY</span><h3>bullions.co.in</h3><p>Server-rendered Ahmedabad association and MCX tables. Cloudflare changes can interrupt collection.</p></article>
          <article><span>SECONDARY</span><h3>allindiabullion.com</h3><p>Server-rendered retail 999 snapshot. Live ticks use a protected channel and are intentionally excluded.</p></article>
          <article><span>DEFINITION</span><h3>Daily open</h3><p>The first same-day IST quote recorded by the worker. Neither source publishes an official opening price.</p></article>
        </div>
      </section>

      <section className="tracker-note"><strong>Migration status</strong><p>The zero-dependency Python tracker, parser fixtures, tests, research and notification documentation now live inside the Trading Lab repository under <code>commodities/gold-price-tracker</code>. Runtime state and credentials remain local and ignored.</p><a href="https://github.com/Prishi-Enterprise/trading-lab/tree/main/commodities/gold-price-tracker">View source module ↗</a></section>

      <footer className="dashboard-footer"><Brand inverse /><p>Observation only · No commodity order or advice is generated</p><span>Signed in as {user.email}</span></footer>
    </main>
  );
}
