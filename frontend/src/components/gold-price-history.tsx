"use client";

import { useState } from "react";
import { money, type GoldUpdate } from "../lib/dashboard";

const SERIES = [
  ["bullions:gold24k_10g", "Ahmedabad bullion 24K"],
  ["bullions:mcx_gold_10g", "India MCX gold"],
  ["suvarnakrupa:gold24k_10g", "Ahmedabad showroom 24K"],
] as const;

function chartTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).format(new Date(value));
}

export function GoldPriceHistory({ updates }: { updates: Pick<GoldUpdate, "observed_at" | "metrics">[] }) {
  const [selected, setSelected] = useState<string>(SERIES[0][0]);
  const points = updates.flatMap((update) => {
    const metric = update.metrics?.find((item) => item.metric === selected);
    return metric && Number.isFinite(metric.price) && metric.price > 0
      ? [{ time: new Date(update.observed_at).getTime(), price: metric.price, observedAt: update.observed_at }]
      : [];
  }).filter((point) => Number.isFinite(point.time)).sort((a, b) => a.time - b.time);
  const first = points[0];
  const last = points.at(-1);
  const min = Math.min(...points.map((point) => point.price));
  const max = Math.max(...points.map((point) => point.price));
  const spread = Math.max(max - min, max * 0.005, 1);
  const floor = min - spread * 0.15;
  const ceiling = max + spread * 0.15;
  const x = (time: number) => 48 + (first && last && last.time !== first.time ? (time - first.time) / (last.time - first.time) * 704 : 352);
  const y = (price: number) => 220 - (price - floor) / (ceiling - floor) * 190;
  const line = points.map((point, index) => `${index ? "L" : "M"} ${x(point.time).toFixed(1)} ${y(point.price).toFixed(1)}`).join(" ");

  return <section className="panel gold-history" aria-label="Captured gold price history">
    <div className="panel-heading"><div><p className="eyebrow">CAPTURED PRICE HISTORY</p><h2>Gold prices over time.</h2></div><label>Source <select value={selected} onChange={(event) => setSelected(event.target.value)}>{SERIES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label></div>
    {points.length ? <>
      <div className="gold-history-summary"><strong>{money(last?.price)}</strong><span>{points.length} captures · {first && chartTime(first.observedAt)} to {last && chartTime(last.observedAt)}</span></div>
      <div className="gold-history-chart"><svg viewBox="0 0 800 270" role="img" aria-label={`Captured prices from ${money(first?.price)} to ${money(last?.price)}; lowest ${money(min)}, highest ${money(max)}`} preserveAspectRatio="none">
        {[0, 1, 2, 3].map((step) => <g key={step}><line x1="48" x2="752" y1={30 + step * 63.3} y2={30 + step * 63.3} className="gold-history-grid" /><text x="5" y={34 + step * 63.3} className="gold-history-axis">{Math.round((ceiling - step / 3 * (ceiling - floor)) / 1000)}k</text></g>)}
        <path d={line} className="gold-history-line" />
        {points.length === 1 && <circle cx={x(points[0].time)} cy={y(points[0].price)} r="5" className="gold-history-point" />}
      </svg></div>
      <div className="gold-history-range"><span>{first && chartTime(first.observedAt)}</span><span>{last && chartTime(last.observedAt)}</span></div>
    </> : <p className="gold-history-empty">No captured price for this source yet.</p>}
    <p className="gold-history-note">Showing up to the latest 1,000 captures. Each point is a captured source snapshot; these are indicative rates, not executable quotes.</p>
  </section>;
}
