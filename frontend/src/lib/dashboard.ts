export type PaperUpdate = {
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

export type Signal = {
  close?: string;
  sma?: string;
  previous_high?: string;
  eligible?: boolean;
  reasons?: string[];
};

export const trialDates = ["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28"];

export function money(value: unknown) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount);
}

export function shortDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).format(new Date(`${value}T12:00:00+05:30`));
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
