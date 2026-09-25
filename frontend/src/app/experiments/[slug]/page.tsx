import Link from "next/link";
import { notFound } from "next/navigation";
import { Brand } from "@/components/brand";
import { LabHeader } from "@/components/lab-header";
import { LiveRefresh } from "@/components/live-refresh";
import { requireTradingMember } from "@/lib/auth";
import { explainReason, localTimestamp, money, nseTrialDates, shortDate, trialStatus, type Experiment, type PaperUpdate, type Signal } from "@/lib/dashboard";

export const dynamic = "force-dynamic";

type ScreenResult = { symbol: string; rule: string; net: string; trades: number; later_net: string };

function istToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}

function metric(value: unknown, fallback = 0) { return money(value ?? fallback); }

export default async function ExperimentDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { supabase, user, membership } = await requireTradingMember();
  const [experimentResult, updatesResult] = await Promise.all([
    supabase.from("experiments").select("*").eq("slug", slug).maybeSingle(),
    supabase.from("paper_updates").select("*").eq("experiment_slug", slug).order("as_of", { ascending: false }),
  ]);
  if (experimentResult.error || updatesResult.error) throw new Error("Could not load experiment results.");
  if (!experimentResult.data) notFound();
  const experiment = experimentResult.data as Experiment;
  const updates = (updatesResult.data ?? []) as PaperUpdate[];
  const latest = updates[0];
  const latestVerified = updates.find((update) => update.status === "verified" || update.status === "complete");
  const portfolio = latestVerified?.portfolio ?? {};
  const isNse = slug === "etf-breakout-nse-v2";
  const isScreen = slug === "fixed-rule-strategy-screen";
  const results = Array.isArray(latest?.details?.results) ? latest.details.results as ScreenResult[] : [];
  const signalUpdate = latestVerified && Object.keys(latestVerified.signals ?? {}).length ? latestVerified : undefined;
  const issues = Array.isArray(latest?.details?.issues) ? latest.details.issues.map(String) : [];
  const trialsLogged = updates.filter((update) => nseTrialDates.includes(update.as_of) && update.status !== "blocked").length;

  return <main className="dashboard-shell experiment-detail-shell">
    <LiveRefresh />
    <LabHeader active="experiments" displayName={membership.display_name || user.email || "Member"} />
    <nav className="tracker-breadcrumb" aria-label="Breadcrumb"><Link href="/">Experiments</Link><span>/</span><strong>{experiment.title}</strong></nav>

    <section className="detail-hero">
      <div><p className="eyebrow">{experiment.category.toUpperCase()} · {experiment.kind.toUpperCase()} EXPERIMENT</p><h1>{experiment.title}</h1><p>{experiment.summary}</p></div>
      <span className={`detail-status ${experiment.status}`}>{experiment.status === "active" && <i />}{experiment.status.toUpperCase()}</span>
    </section>

    <section className="detail-context"><div><small>PERIOD</small><strong>{experiment.started_on ? shortDate(experiment.started_on) : "—"}{experiment.ends_on && experiment.ends_on !== experiment.started_on ? ` — ${shortDate(experiment.ends_on)}` : ""}</strong></div><div><small>METHOD</small><p>{experiment.method}</p></div><div><small>LAST UPDATE</small><strong>{latest ? localTimestamp(latest.recorded_at) : "First close pending"}</strong></div></section>

    {latest ? <section className={`status-banner detail-banner ${latest.status}`}><div className="status-icon" aria-hidden="true">{latest.status === "blocked" ? "!" : "✓"}</div><div><p className="eyebrow">LATEST RESULT · {shortDate(latest.as_of).toUpperCase()}</p><h2>{latest.headline}</h2><p>{latest.summary}</p></div><span className="status-tag">{latest.status.toUpperCase()}</span></section>
      : <section className="status-banner detail-banner awaiting"><div className="status-icon" aria-hidden="true">·</div><div><p className="eyebrow">AWAITING FIRST RECORD</p><h2>Results begin after the completed NSE session.</h2><p>The cloud worker checks official data after market close. Missing or inconsistent data will be shown as a blocker.</p></div></section>}

    {isNse && <>
      <section className="metric-grid detail-metrics" aria-label="NSE paper portfolio"><article><p>Paper equity</p><strong>{metric(portfolio.ending_equity, 28000)}</strong><span>Simulated capital only</span></article><article><p>Paper net P&amp;L</p><strong className={Number(portfolio.net ?? 0) < 0 ? "negative" : ""}>{metric(portfolio.net)}</strong><span>After estimated fills and fees</span></article><article><p>Closed trades</p><strong>{Array.isArray(portfolio.trades) ? portfolio.trades.length : 0}</strong><span>Live orders disabled</span></article><article><p>Valid sessions</p><strong>{trialsLogged} / 5</strong><span>25 Sep – 1 Oct</span></article></section>
      <section className="content-grid detail-grid"><article className="panel trial-panel"><div className="panel-heading"><div><p className="eyebrow">PROSPECTIVE RECORD</p><h2>Five-session paper week</h2></div><span>{trialsLogged} / 5 frozen</span></div><div className="session-list">{nseTrialDates.map((date, index) => {
        const status = trialStatus(date, updates, istToday());
        return <div className={`session-row ${status}`} key={date}><span className="session-number">0{index + 1}</span><div><strong>{shortDate(date)}</strong><small>{date === "2026-10-01" ? "Final review" : "Official NSE close"}</small></div><span className="session-status"><i />{({ blocked: "Blocked", complete: "Complete", recorded: "Recorded", awaiting: "Awaiting close", missing: "Missing", upcoming: "Upcoming" } as const)[status]}</span></div>;
      })}</div></article><article className="panel rules-panel"><p className="eyebrow">FROZEN RISK RULES</p><h2>Paper controls</h2><dl><div><dt>Starting paper capital</dt><dd>₹28,000</dd></div><div><dt>Maximum position</dt><dd>₹10,000</dd></div><div><dt>Planned risk per trade</dt><dd>₹250 incl. costs</dd></div><div><dt>Total paper loss limit</dt><dd>₹5,000</dd></div><div><dt>Positions</dt><dd>One maximum</dd></div><div><dt>Order routing</dt><dd>Disabled</dd></div></dl></article></section>
      {signalUpdate && <section className="panel signals-panel"><div className="panel-heading"><div><p className="eyebrow">FROZEN AFTER NSE CLOSE · {shortDate(signalUpdate.as_of).toUpperCase()}</p><h2>Next-session paper screen</h2></div><span>{Object.values(signalUpdate.signals).filter((plan: Signal) => plan.eligible).length} eligible</span></div><div className="signal-grid">{Object.entries(signalUpdate.signals).map(([symbol, signal]) => <article className="signal-card" key={symbol}><div className="signal-title"><div><span>{symbol.replace(".NS", "")}</span><small>Official NSE ETF row</small></div><b>{signal.eligible ? "SETUP" : "PASS"}</b></div><div className="signal-values"><div><span>Close</span><strong>{metric(signal.close)}</strong></div><div><span>SMA 200</span><strong>{metric(signal.sma)}</strong></div><div><span>20d high</span><strong>{metric(signal.previous_high)}</strong></div></div><ul>{signal.reasons?.map((reason) => <li key={reason}>{explainReason(reason)}</li>)}</ul></article>)}</div></section>}
      <section className="tracker-note"><strong>Source and timing</strong><p>Daily bars come from the official NSE cash-market bhavcopy. The Supabase worker validates the completed session, checks frozen history and records one prospective decision for the next session. This page refreshes every minute while open.</p>{typeof latestVerified?.details?.source_url === "string" && <a href={latestVerified.details.source_url}>Latest NSE archive ↗</a>}</section>
    </>}

    {isScreen && <section className="panel screen-results"><div className="panel-heading"><div><p className="eyebrow">RETROSPECTIVE SCREEN · 284 VALIDATED SESSIONS</p><h2>Fixed hypotheses, recorded outcomes</h2></div><span>17 Sep 2025 – 24 Sep 2026</span></div><div className="screen-table-wrap"><table><thead><tr><th>ETF</th><th>Rule</th><th>Full-window net</th><th>Trades</th><th>Later-slice net</th></tr></thead><tbody>{results.map((row) => <tr key={`${row.symbol}-${row.rule}`}><td>{row.symbol.replace(".NS", "")}</td><td>{row.rule}</td><td className={Number(row.net) < 0 ? "negative" : ""}>{money(row.net)}</td><td>{row.trades}</td><td className={Number(row.later_net) < 0 ? "negative" : ""}>{money(row.later_net)}</td></tr>)}</tbody></table></div><p className="panel-note">The later slice was reviewed in the same research pass and is not untouched validation. No-trade rows are inactivity, not successful returns.</p><a className="text-link" href="https://github.com/Prishi-Enterprise/trading-lab/blob/main/reports/2026-09-25-open-strategy-screen.md">Read method and limitations ↗</a></section>}

    {issues.length > 0 && <section className="panel issue-panel"><div><p className="eyebrow">DATA QUALITY</p><h2>What blocked the check</h2></div><div className="issue-list">{issues.map((issue) => <p key={issue}><span>!</span>{issue}</p>)}</div></section>}

    {!isScreen && <section className="panel experiment-timeline"><div className="panel-heading"><div><p className="eyebrow">AUDIT TRAIL</p><h2>Daily results</h2></div><span>{updates.length} recorded</span></div><div className="timeline-list">{updates.length ? updates.map((update) => <article key={update.as_of}><span>{shortDate(update.as_of)}</span><div><strong>{update.headline}</strong><p>{update.summary}</p></div><small className={update.status}>{update.status}</small></article>) : <p className="empty-note">No completed session has been recorded yet.</p>}</div></section>}

    <footer className="dashboard-footer"><Brand inverse /><p>Private research dashboard · No brokerage connection or live order</p><span>Signed in as {user.email}</span></footer>
  </main>;
}
