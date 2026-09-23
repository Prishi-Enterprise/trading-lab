import { Brand } from "@/components/brand";
import { EmailLoginForm } from "@/components/email-login-form";
import { isConfigured } from "@/lib/config";

export default function LoginPage() {
  return (
    <main className="login-layout">
      <section className="login-story">
        <Brand inverse />
        <div className="login-copy">
          <p className="eyebrow">A DISCIPLINED PAPER EXPERIMENT</p>
          <h1>Follow the process.<br /><span>Protect the capital.</span></h1>
          <p>One private place to review signals, decisions, data checks and the evidence behind our trading idea.</p>
        </div>
        <footer><a href="https://www.prishi.in">Prishi / India</a> <span>•</span> Paper trading only</footer>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <span className="badge"><span className="shield" aria-hidden="true">✓</span> Private access</span>
          <h2>Welcome to<br />Trading Lab.</h2>
          <p className="muted">Sign in with the code sent to your invited email.</p>
          <EmailLoginForm configured={isConfigured()} />
          <div className="privacy-note">
            <span className="shield" aria-hidden="true">✓</span>
            <p>This dashboard shows research and simulated results. It cannot place trades or access a brokerage account.</p>
          </div>
          <a className="prishi-home-link" href="https://www.prishi.in">← Back to prishi.in</a>
        </div>
      </section>
    </main>
  );
}
