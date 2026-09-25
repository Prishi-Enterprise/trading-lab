import Link from "next/link";
import { Brand } from "@/components/brand";
import { LabHeader } from "@/components/lab-header";
import { LiveRefresh } from "@/components/live-refresh";
import { requireTradingMember } from "@/lib/auth";
import { localTimestamp, money, shortDate, type Experiment, type GoldUpdate, type PaperUpdate } from "@/lib/dashboard";

export const dynamic = "force-dynamic";

function experimentLabel(experiment: Experiment) {
  if (experiment.status === "active") return "LIVE PAPER WEEK";
  if (experiment.status === "stopped") return "STOPPED · DATA ISSUE";
  return "HISTORICAL SCREEN";
}

function latestSummary(experiment: Experiment, update?: PaperUpdate) {
  if (update) return update.headline;
  if (experiment.status === "active") return "First completed NSE close pending";
  return "Record available";
}

export default async function TradingLabHome() {
  const { supabase, user, membership } = await requireTradingMember();
  const [experimentResult, paperResult, goldResult] = await Promise.all([
    supabase.from("experiments").select("*").order("display_order", { ascending: true }),
    supabase.from("paper_updates").select("*").order("as_of", { ascending: false }),
    supabase.from("gold_updates").select("observed_at,status,headline").order("observed_at", { ascending: false }).limit(1),
  ]);
  if (experimentResult.error || paperResult.error || goldResult.error) throw new Error("Could not load the experiment index.");
  const experiments = (experimentResult.data ?? []) as Experiment[];
  const updates = (paperResult.data ?? []) as PaperUpdate[];
  const gold = (goldResult.data?.[0] ?? null) as Pick<GoldUpdate, "observed_at" | "status" | "headline"> | null;
  const active = experiments.find((experiment) => experiment.status === "active");
  const activeUpdate = updates.find((update) => update.experiment_slug === active?.slug);
  const activePortfolio = activeUpdate?.portfolio ?? {};
  const otherExperiments = experiments.filter((experiment) => experiment.slug !== active?.slug);

  return (
    <main className="dashboard-shell experiment-shell">
      <LiveRefresh />
      <LabHeader active="experiments" displayName={membership.display_name || user.email || "Member"} />

      <section className="experiment-hero">
        <div>
          <p className="eyebrow">PRISHI · TRADING LAB</p>
          <h1>Every experiment.<br /><span>Every outcome.</span></h1>
          <p>Follow paper decisions and research results as they are recorded. Each run keeps its own rules, sources and limits.</p>
        </div>
        <div className="hero-index" aria-label="Experiment count"><strong>{String(experiments.length).padStart(2, "0")}</strong><span>recorded<br />experiments</span></div>
      </section>

      {active && (
        <section className="featured-experiment" aria-labelledby="active-experiment-heading">
          <div className="featured-top"><span className="live-dot" /><span>ACTIVE EXPERIMENT</span><span className="featured-date">{active.started_on && shortDate(active.started_on)} — {active.ends_on && shortDate(active.ends_on)}</span></div>
          <div className="featured-body">
            <div><p className="eyebrow">{active.category.toUpperCase()} · OFFICIAL NSE DATA</p><h2 id="active-experiment-heading">{active.title}</h2><p>{active.summary}</p></div>
            <div className="featured-measure"><small>SIMULATED EQUITY</small><strong>{money(activePortfolio.ending_equity ?? 28000)}</strong><span>{activeUpdate ? `Last check ${localTimestamp(activeUpdate.recorded_at)}` : "First daily record after market close"}</span></div>
          </div>
          <div className="featured-bottom"><span><i className={activeUpdate?.status === "blocked" ? "alert-dot" : ""} />{latestSummary(active, activeUpdate)}</span><Link href={`/experiments/${active.slug}`}>View experiment details <b aria-hidden="true">↗</b></Link></div>
        </section>
      )}

      <section className="experiment-section">
        <div className="section-intro"><div><p className="eyebrow">RESEARCH ARCHIVE</p><h2>Other experiments</h2></div><p>Stopped and completed work stays visible, including failed hypotheses and data problems.</p></div>
        <div className="experiment-grid">
          {otherExperiments.map((experiment) => {
            const update = updates.find((item) => item.experiment_slug === experiment.slug);
            return <article className="experiment-card" key={experiment.slug}>
              <div className="experiment-card-top"><span>{experimentLabel(experiment)}</span><small>{experiment.kind}</small></div>
              <h3>{experiment.title}</h3><p>{experiment.summary}</p>
              <div className="experiment-card-bottom"><span>{update ? latestSummary(experiment, update) : "No update yet"}</span><Link href={`/experiments/${experiment.slug}`}>Details <b aria-hidden="true">→</b></Link></div>
            </article>;
          })}
        </div>
      </section>

      <section className="experiment-tool-strip"><div><p className="eyebrow">MARKET OBSERVATION</p><h2>Gold Price Tracker</h2><p>Ahmedabad gold and MCX snapshots, kept separate from paper strategy results.</p></div><div><span>{gold ? `${gold.status.toUpperCase()} · ${localTimestamp(gold.observed_at)}` : "AWAITING SOURCE DATA"}</span><Link href="/commodities/gold">Open tracker <b aria-hidden="true">↗</b></Link></div></section>
      <footer className="dashboard-footer"><Brand inverse /><p>Private research dashboard · Simulated outcomes are not trading income</p><span>Signed in as {user.email}</span></footer>
    </main>
  );
}
