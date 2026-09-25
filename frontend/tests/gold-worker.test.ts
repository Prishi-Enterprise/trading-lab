import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { resolve } from "node:path";
import ts from "typescript";
import { afterEach, describe, expect, it, vi } from "vitest";

type Worker = (request: Request) => Promise<Response>;

function worker(fetchMock: typeof fetch, secrets: Record<string, string>) {
  let handler: Worker | undefined;
  const source = readFileSync(resolve(process.cwd(), "supabase/functions/gold-tracker/index.ts"), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;
  runInNewContext(compiled, {
    Deno: { env: { get: (key: string) => secrets[key] }, serve: (fn: Worker) => { handler = fn; } },
    fetch: fetchMock, Response, URL, AbortSignal, Date, Intl, Set, Map, Promise, Number, String, JSON, Error,
  });
  if (!handler) throw new Error("Worker did not register a handler");
  return handler;
}

afterEach(() => vi.useRealTimers());

describe("hosted gold alert email", () => {
  it("queues and emails a threshold crossing only once per metric and IST day", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-25T04:30:00Z"));
    const bullionPage = '<i>Last Update</i>: <strong>Friday, 25 Sep 2026 10:00 AM</strong><td class="text-left">Gold 24 Karat</td><td>149000</td><td>153000</td>';
    let latest: Record<string, unknown> | undefined;
    let queued: Array<Record<string, unknown>> = [];
    let emailCount = 0;
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/rpc/verify_worker_secret")) return Response.json(true);
      if (url.includes("/rest/v1/gold_updates") && init?.method === "POST") {
        latest = JSON.parse(String(init.body));
        return new Response(null, { status: 201 });
      }
      if (url.includes("/rest/v1/gold_updates") && url.includes("observed_on=eq.")) return Response.json(latest ? [latest] : [{
        metrics: [{ metric: "bullions:gold24k_10g", open_price: 150000, open_at: "09:00 IST", alerts_sent: [] }],
      }]);
      if (url.includes("/rest/v1/gold_updates")) return Response.json([]);
      if (url.includes("/rest/v1/gold_alert_deliveries") && init?.method === "POST") {
        queued = JSON.parse(String(init.body));
        return new Response(null, { status: 201 });
      }
      if (url.includes("/rest/v1/gold_alert_deliveries") && init?.method === "PATCH") {
        queued[0].status = "sent";
        return new Response(null, { status: 204 });
      }
      if (url.includes("/rest/v1/gold_alert_deliveries")) return Response.json(queued.filter((row) => row.status === "pending"));
      if (url === "https://api.resend.com/emails") {
        emailCount += 1;
        return Response.json({ id: "mail-1" });
      }
      if (url.includes("bullions.co.in")) return new Response(bullionPage);
      throw new Error("Other source unavailable in test");
    });
    const handler = worker(fetchMock as typeof fetch, {
      SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "test-service-key",
      RESEND_API_KEY: "test-mail-key", GOLD_ALERT_FROM: "Gold Tracker <alerts@auth.prishi.in>", GOLD_ALERT_TO: "owner@example.test",
    });
    const request = () => new Request("https://example.supabase.co/functions/v1/gold-tracker", { headers: { "x-worker-secret": "test-worker-secret" } });
    const first = await (await handler(request())).json();
    const second = await (await handler(request())).json();
    expect(first.new_alerts).toBe(1);
    expect(second.new_alerts).toBe(0);
    expect(queued).toHaveLength(1);
    expect(queued[0].threshold).toBe(2);
    expect(emailCount).toBe(1);
  });

  it("retries a pending threshold event and records provider acceptance", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-25T04:30:00Z"));
    const pending = {
      observed_on: "2026-09-25", metric: "bullions:gold24k_10g", threshold: 2,
      label: "Gold 24K /10g (Ahmedabad bullion rate)", price: 153000,
      open_price: 150000, change_pct: 2, triggered_at: "2026-09-25T04:15:00Z",
      status: "pending", attempts: 0,
    };
    let sentBody: Record<string, unknown> | undefined;
    const savedBodies: Array<Record<string, unknown>> = [];
    let emailCount = 0;
    let key: string | null | undefined;
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/rpc/verify_worker_secret")) return Response.json(true);
      if (url.includes("/rest/v1/gold_updates") && init?.method === "POST") return new Response(null, { status: 201 });
      if (url.includes("/rest/v1/gold_updates")) return Response.json([]);
      if (url.includes("/rest/v1/gold_alert_deliveries") && init?.method === "PATCH") {
        savedBodies.push(JSON.parse(String(init.body)));
        return new Response(null, { status: 204 });
      }
      if (url.includes("/rest/v1/gold_alert_deliveries")) return Response.json([
        { ...pending, observed_on: "2026-09-24", triggered_at: "2026-09-24T04:15:00Z" },
        pending,
      ]);
      if (url === "https://api.resend.com/emails") {
        emailCount += 1;
        sentBody = JSON.parse(String(init?.body));
        key = new Headers(init?.headers).get("Idempotency-Key");
        return Response.json({ id: "mail-1" });
      }
      throw new Error("Source unavailable in test");
    });
    const handler = worker(fetchMock as typeof fetch, {
      SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "test-service-key",
      RESEND_API_KEY: "test-mail-key", GOLD_ALERT_FROM: "Gold Tracker <alerts@auth.prishi.in>", GOLD_ALERT_TO: "owner@example.test",
    });
    const response = await handler(new Request("https://example.supabase.co/functions/v1/gold-tracker", { headers: { "x-worker-secret": "test-worker-secret" } }));
    expect(response.status).toBe(200);
    expect((await response.json()).email).toEqual({ state: "configured", sent: 1 });
    expect(sentBody?.to).toEqual(["owner@example.test"]);
    expect(key).toBe("gold-2026-09-25-bullions:gold24k_10g-2");
    expect(emailCount).toBe(1);
    expect(savedBodies.map((row) => row.status)).toEqual(["expired", "sent"]);
    expect(savedBodies[1].provider_id).toBe("mail-1");
  });
});
