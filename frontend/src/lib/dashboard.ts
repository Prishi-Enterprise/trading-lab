export type PaperUpdate = {
  experiment_slug?: string;
  as_of: string;
  recorded_at: string;
  status: "verified" | "blocked" | "complete";
  headline: string;
  summary: string;
  portfolio: Record<string, unknown>;
  signals: Record<string, Signal>;
  details: Record<string, unknown>;
  source: string;
};

export type Experiment = {
  slug: string;
  title: string;
  kind: "prospective" | "retrospective";
  status: "active" | "stopped" | "complete";
  category: string;
  started_on: string | null;
  ends_on: string | null;
  summary: string;
  method: string;
  display_order: number;
};

export const nseTrialDates = ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"];

export type Signal = {
  close?: string;
  sma?: string;
  previous_high?: string;
  eligible?: boolean;
  reasons?: string[];
};

export type GoldMetric = {
  metric: string;
  label: string;
  price: number;
  unit: string;
  as_of: string | null;
  checked_at: string;
  open_price: number | null;
  open_at: string | null;
  change_pct: number | null;
  alerts_sent: number[];
};

export type GoldUpdate = {
  observed_at: string;
  observed_on: string;
  status: "verified" | "partial" | "failed";
  headline: string;
  summary: string;
  metrics: GoldMetric[];
  issues: string[];
  interval_minutes: number;
  source: string;
};

export const trialDates = ["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28"];

export function money(value: unknown) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount);
}

export function shortDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).format(new Date(`${value}T12:00:00+05:30`));
}

export function localTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).format(new Date(value));
}

export function trialStatus(date: string, updates: PaperUpdate[], today: string) {
  const update = updates.find((item) => item.as_of === date);
  if (update) return update.status === "blocked" ? "blocked" : update.status === "complete" ? "complete" : "recorded";
  if (date === today) return "awaiting";
  return date < today ? "missing" : "upcoming";
}

export function explainReason(reason: string) {
  const labels: Record<string, string> = {
    close_not_above_200_session_average: "Close is below its 200-session average",
    no_close_above_previous_20_session_high: "No close above the previous 20-session high",
    stale_daily_bar: "Daily price is stale",
  };
  return labels[reason] ?? reason.replaceAll("_", " ");
}
