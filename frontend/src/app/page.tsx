import { Brand } from "@/components/brand";
import { requireTradingMember } from "@/lib/auth";
import { explainReason, money, shortDate, trialDates, trialStatus, type PaperUpdate } from "@/lib/dashboard";

export const dynamic = "force-dynamic";

function statusLabel(status: ReturnType<typeof trialStatus>) {
  return { blocked: "Blocked", complete: "Complete", recorded: "Recorded", awaiting: "Review due", missing: "Missed", upcoming: "Upcoming" }[status];
}

export default async function Dashboard() {
  const { supabase, user, membership } = await requireTradingMember();
  const { data, error } = await supabase.from("paper_updates").select("*").order("as_of", { ascending: false });
  if (error) throw new Error("Could not load the paper-trading record.");

  const updates = (data ?? []) as PaperUpdate[];
  const latest = updates[0];
  const signalUpdate = updates.find((item) => Object.keys(item.signals ?? {}).length > 0);
  const portfolio = latest?.portfolio ?? {};
  const net = Number(portfolio.net ?? 0);
  const riskUsed = Math.max(0, -net);
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  const issues = Array.isArray(latest?.details?.issues) ? latest.details.issues.map(String) : [];

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <Brand inverse />
        <div className="topbar-meta">
          <span className="mode-pill"><i /> PAPER ONLY</span>
          <span className="user-name">{membership.display_name || user.email}</span>
          <form action="/auth/signout" method="post"><button className="signout-button">Sign out</button></form>
        </div>
      </header>

      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">ETF BREAKOUT · FROZEN V1</p>
          <h1>The evidence,<br /><span>without the noise.</span></h1>
        </div>
        <div className="hero-note">
          <p>One week to test the process: data checks, prospective signals, simulated execution and risk discipline.</p>
          <span>22–28 SEP 2026 <b>•</b> 5 SESSIONS</span>
        </div>
      </section>

      {latest && (
        <section className={`status-banner ${latest.status}`}>
          <div className="status-icon" aria-hidden="true">{latest.status === "blocked" ? "!" : "✓"}</div>
          <div>
            <p className="eyebrow">LATEST REVIEW · {shortDate(latest.as_of).toUpperCase()}</p>
            <h2>{latest.headline}</h2>
            <p>{latest.summary}</p>
          </div>
          <span className="status-tag">{latest.status === "blocked" ? "NO DECISION" : latest.status.toUpperCase()}</span>
        </section>
      )}

      <section className="metric-grid" aria-label="Paper portfolio summary">
        <article><p>Paper equity</p><strong>{money(portfolio.ending_equity ?? 28000)}</strong><span>Simulated, not deposited</span></article>
        <article><p>Net P&amp;L</p><strong className={net < 0 ? "negative" : ""}>{money(net)}</strong><span>Realised + open-position mark</span></article>
        <article><p>Completed trades</p><strong>{Array.isArray(portfolio.trades) ? portfolio.trades.length : 0}</strong><span>No live orders</span></article>
        <article><p>Loss capacity used</p><strong>{money(riskUsed)}</strong><span>{money(5000 - riskUsed)} remains before review halt</span></article>
      </section>

      <section className="content-grid">
        <article className="panel trial-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">PROSPECTIVE PAPER WEEK</p><h2>Five-session record</h2></div>
            <span>{updates.filter((item) => trialDates.includes(item.as_of)).length} / 5 logged</span>
          </div>
          <div className="session-list">
            {trialDates.map((date, index) => {
              const status = trialStatus(date, updates, today);
              return (
                <div className={`session-row ${status}`} key={date}>
                  <span className="session-number">0{index + 1}</span>
                  <div><strong>{shortDate(date)}</strong><small>{date === "2026-09-28" ? "Final review" : "Market close review"}</small></div>
                  <span className="session-status"><i />{statusLabel(status)}</span>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel goal-panel">
          <p className="eyebrow">THE AFFORDABILITY GOAL</p>
          <h2>Keep income and experiments separate.</h2>
          <div className="goal-number"><strong>{money(0)}</strong><span>actual trading contribution</span></div>
          <div className="progress-track"><span style={{ width: "0%" }} /></div>
          <div className="goal-labels"><span>₹0</span><span>Half-cost reference ₹5,500</span></div>
          <p className="panel-note">The ₹5,500 and ₹11,000 subscription figures are planning references, not expected returns. Paper profit does not pay a bill.</p>
        </article>
      </section>

      {issues.length > 0 && (
        <section className="panel issue-panel">
          <div><p className="eyebrow">WHY THE PROCESS STOPPED</p><h2>Conflicting data means no new paper instruction.</h2></div>
          <div className="issue-list">
            {issues.map((issue) => <p key={issue}><span>!</span>{issue}</p>)}
          </div>
        </section>
      )}

      <section className="panel signals-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">LAST VERIFIED SCREEN · {signalUpdate ? shortDate(signalUpdate.as_of).toUpperCase() : "—"}</p><h2>What the rules saw</h2></div>
          <span>No setup</span>
        </div>
        <div className="signal-grid">
          {Object.entries(signalUpdate?.signals ?? {}).map(([symbol, signal]) => (
            <article className="signal-card" key={symbol}>
              <div className="signal-title"><div><span>{symbol.replace(".NS", "")}</span><small>NSE equity ETF</small></div><b>PASS</b></div>
              <div className="signal-values"><div><span>Close</span><strong>₹{Number(signal.close).toFixed(2)}</strong></div><div><span>SMA 200</span><strong>₹{Number(signal.sma).toFixed(2)}</strong></div><div><span>20d high</span><strong>₹{Number(signal.previous_high).toFixed(2)}</strong></div></div>
              <ul>{signal.reasons?.map((reason) => <li key={reason}>{explainReason(reason)}</li>)}</ul>
            </article>
          ))}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="panel rules-panel">
          <p className="eyebrow">FROZEN RISK RULES</p><h2>Small enough to survive mistakes.</h2>
          <dl><div><dt>Paper capital</dt><dd>₹28,000</dd></div><div><dt>Maximum position</dt><dd>₹10,000</dd></div><div><dt>Planned risk / trade</dt><dd>₹250 incl. costs</dd></div><div><dt>Total loss limit</dt><dd>₹5,000</dd></div><div><dt>Open positions</dt><dd>One maximum</dd></div><div><dt>Live execution</dt><dd>Disabled</dd></div></dl>
        </article>
        <article className="panel evidence-panel">
          <p className="eyebrow">HISTORICAL EVIDENCE</p><h2>The baseline has not earned trust.</h2>
          <div className="evidence-table"><div><span>2018–22</span><strong className="negative">−₹2,249.29</strong><small>15 trades</small></div><div><span>2023–25</span><strong>+₹482.91</strong><small>10 trades</small></div><div><span>2026 YTD</span><strong className="negative">−₹70.44</strong><small>1 trade</small></div></div>
          <p className="panel-note">A five-session operations test can uncover process errors. It cannot establish profitability or justify live capital.</p>
        </article>
      </section>

      <footer className="dashboard-footer"><Brand inverse /><p>Private research dashboard · Prices checked against NSE · Brokerage disconnected</p><span>Signed in as {user.email}</span></footer>
    </main>
  );
}
