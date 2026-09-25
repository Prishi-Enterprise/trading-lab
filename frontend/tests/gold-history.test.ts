import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { GoldPriceHistory } from "../src/components/gold-price-history";
import type { GoldMetric } from "../src/lib/dashboard";

function capture(observed_at: string, price: number) {
  return {
    observed_at,
    metrics: [{ metric: "bullions:gold24k_10g", price } as GoldMetric],
  };
}

describe("gold price history", () => {
  it("renders recorded prices as a chart with accessible range and capture count", () => {
    const html = renderToStaticMarkup(createElement(GoldPriceHistory, { updates: [
      capture("2026-09-25T04:00:00Z", 150000),
      capture("2026-09-25T05:00:00Z", 153000),
    ] }));
    expect(html).toContain("2 captures");
    expect(html).toContain("Captured prices from");
    expect(html).toContain("1,50,000");
    expect(html).toContain("1,53,000");
    expect(html).toContain("gold-history-line");
  });

  it("shows an honest empty state when there are no captures", () => {
    const html = renderToStaticMarkup(createElement(GoldPriceHistory, { updates: [] }));
    expect(html).toContain("No captured price for this source yet.");
  });
});
