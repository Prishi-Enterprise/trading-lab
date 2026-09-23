"use client";

import { useActionState, useEffect, useState } from "react";
import { emailLogin } from "@/app/login/actions";
import type { LoginState } from "@/lib/login-validation";

const initial: LoginState = { email: "", step: "email" };

export function EmailLoginForm({ configured }: { configured: boolean }) {
  const [state, action, pending] = useActionState(emailLogin, initial);
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    if (!state.sent) return;
    const update = () => setRemaining(Math.max(0, 60 - Math.floor((Date.now() - state.sent!) / 1000)));
    const timeout = setTimeout(update, 0);
    const timer = setInterval(update, 1000);
    return () => { clearTimeout(timeout); clearInterval(timer); };
  }, [state.sent]);

  return (
    <form action={action} className="otp-form">
      {state.error && <p className="notice error" role="alert">{state.error}</p>}
      {state.message && <p className="notice" role="status">{state.message}</p>}
      {state.step === "email" ? (
        <>
          <label>
            Email address
            <input name="email" type="email" autoComplete="email" defaultValue={state.email} required maxLength={254} placeholder="Your invited email address" />
          </label>
          <button className="primary-button" name="intent" value="send" disabled={pending || !configured}>
            {pending ? "Sending…" : "Send sign-in code"}
          </button>
        </>
      ) : (
        <>
          <p className="form-context">Sign in as <strong>{state.email}</strong></p>
          <input type="hidden" name="email" value={state.email} />
          <label>
            Sign-in code
            <input key={state.sent} name="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} required autoFocus placeholder="6-digit code" />
          </label>
          <small>The code expires in 10 minutes. Only the latest code works.</small>
          <button className="primary-button" name="intent" value="verify" disabled={pending}>
            {pending ? "Please wait…" : "Verify and sign in"}
          </button>
          <div className="otp-options">
            <button className="text-button" name="intent" value="resend" formNoValidate disabled={pending || remaining > 0}>
              {remaining > 0 ? `Resend in ${remaining}s` : "Resend code"}
            </button>
            <button className="text-button" name="intent" value="change" formNoValidate disabled={pending}>Change email</button>
          </div>
        </>
      )}
    </form>
  );
}
