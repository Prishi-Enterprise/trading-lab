import { describe, expect, it } from "vitest";
import { explainReason, money, trialStatus, type PaperUpdate } from "../src/lib/dashboard";
import { loginCode } from "../src/lib/login-validation";

const blocked: PaperUpdate = {
  as_of: "2026-09-22",
  recorded_at: "2026-09-22T17:36:39+05:30",
  status: "blocked",
  headline: "Blocked",
  summary: "Data conflict",
  portfolio: {}, signals: {}, details: {}, source: "audit",
};

describe("dashboard presentation", () => {
  it("keeps a blocked paper session visibly blocked", () => {
    expect(trialStatus("2026-09-22", [blocked], "2026-09-23")).toBe("blocked");
  });

  it("distinguishes today's pending review from future sessions", () => {
    expect(trialStatus("2026-09-23", [], "2026-09-23")).toBe("awaiting");
    expect(trialStatus("2026-09-24", [], "2026-09-23")).toBe("upcoming");
  });

  it("formats the paper balance without implying a live account", () => {
    expect(money("28000.00")).toContain("28,000");
  });

  it("turns strategy reason codes into readable text", () => {
    expect(explainReason("no_close_above_previous_20_session_high")).toBe("No close above the previous 20-session high");
  });

  it("accepts the eight-digit code sent by Supabase", () => {
    expect(loginCode.safeParse("12345678").success).toBe(true);
    expect(loginCode.safeParse("123456").success).toBe(false);
  });
});
