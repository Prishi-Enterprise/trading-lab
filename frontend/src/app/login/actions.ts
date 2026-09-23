"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { isConfigured } from "@/lib/config";
import { loginCode, loginEmail, type LoginState } from "@/lib/login-validation";

export async function emailLogin(previous: LoginState, form: FormData): Promise<LoginState> {
  const email = loginEmail.safeParse(form.get("email"));
  if (!email.success) return { email: "", step: "email", error: "Enter a valid email address." };

  const value = email.data;
  const intent = form.get("intent");
  if (intent === "change") return { email: value, step: "email" };
  if (!isConfigured()) {
    return { email: value, step: "email", error: "Sign-in is still being configured." };
  }

  const supabase = await createClient();
  if (intent === "verify") {
    const code = loginCode.safeParse(form.get("code"));
    if (!code.success) {
      return { ...previous, email: value, step: "code", error: "Enter the six-digit code from your email." };
    }

    const { error } = await supabase.auth.verifyOtp({ email: value, token: code.data, type: "email" });
    if (error) {
      return { ...previous, email: value, step: "code", error: "That code is invalid or expired. Request a new code and try again." };
    }

    const { data: claimed, error: claimError } = await supabase.rpc("claim_trading_membership");
    if (claimError || !claimed) redirect("/access-pending");
    redirect("/");
  }

  const { error } = await supabase.auth.signInWithOtp({
    email: value,
    options: { shouldCreateUser: true },
  });
  if (error?.status === 429 || error?.code === "over_email_send_rate_limit") {
    return { email: value, step: previous.step, error: "Please wait a minute before requesting another code." };
  }
  if (error) {
    return { email: value, step: "email", error: "Could not send a sign-in code. Use the email invited to Trading Lab." };
  }

  return {
    email: value,
    step: "code",
    sent: Date.now(),
    message: "If this email has access, a code is on its way. Check your inbox and spam folder.",
  };
}
