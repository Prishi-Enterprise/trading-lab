import Link from "next/link";
import { Brand } from "@/components/brand";
import { LabHeader } from "@/components/lab-header";
import { requireTradingMember } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function CommoditiesDashboard() {
  const { user, membership } = await requireTradingMember();

  return (
    <main className="dashboard-shell commodities-shell">
      <LabHeader active="commodities" displayName={membership.display_name || user.email || "Member"} />

      <section className="dashboard-hero commodity-hero">
        <div>
          <p className="eyebrow">COMMODITIES · OBSERVATION FIRST</p>
          <h1>Track the market.<br /><span>Keep claims measured.</span></h1>
        </div>
        <div className="hero-note">
          <p>Commodity tools live beside the stocks experiment while keeping their sources, schedules and evidence separate.</p>
          <span>NO BROKER CONNECTION <b>•</b> NO AUTOMATIC ORDERS</span>
        </div>
      </section>

      <section className="section-intro">
        <div><p className="eyebrow">COMMODITY TOOLS</p><h2>One home for focused trackers.</h2></div>
        <p>The first module watches Ahmedabad gold prices and records threshold events. It does not recommend a trade.</p>
      </section>

      <section className="tool-grid">
        <Link className="tool-card gold-card" href="/commodities/gold">
          <div className="tool-visual" aria-hidden="true"><span>Au</span><i /><i /><i /></div>
          <div className="tool-copy">
            <div className="tool-title"><p className="eyebrow">GOLD · AHMEDABAD</p><span className="status-chip amber">MIGRATED</span></div>
            <h2>Gold Price Tracker</h2>
            <p>Association, MCX and retail 999 snapshots with daily-open comparisons and measured alert thresholds.</p>
            <ul><li>Two public sources</li><li>₹ / 10g metrics</li><li>±2 / ±5 / ±10% alerts</li></ul>
            <strong>Open tracker <span aria-hidden="true">→</span></strong>
          </div>
        </Link>
        <article className="tool-card placeholder-card">
          <div><p className="eyebrow">NEXT MODULE</p><h2>Commodity ideas stay empty until evidence earns a place.</h2></div>
          <p>No placeholder quote, signal or return is treated as market data.</p>
        </article>
      </section>

      <footer className="dashboard-footer"><Brand inverse /><p>Private research dashboard · Commodity observations are informational</p><span>Signed in as {user.email}</span></footer>
    </main>
  );
}
