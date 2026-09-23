"""Freeze prospective paper decisions and replay only pre-recorded signals."""
import argparse
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .research import IST, ROOT, load_bars, run_backtest


def prefix_hash(series, until):
    rows = {symbol: [[str(b.day), str(b.open), str(b.high), str(b.low), str(b.close), b.volume]
                     for b in bars if date(2025,1,1) <= b.day <= until]
            for symbol, bars in series.items()}
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Record a prospective paper snapshot; never sends orders")
    parser.add_argument("--asof", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    now = datetime.now(IST)
    if args.asof != now.date() or now.hour < 16:
        parser.error("Prospective snapshots must be recorded today after 16:00 IST; no backdating")
    config_bytes = (ROOT/"research-config.json").read_bytes()
    config_hash = hashlib.sha256(config_bytes).hexdigest()
    cfg = json.loads(config_bytes)
    if cfg["mode"] != "paper":
        parser.error("Only paper mode supported")
    trial_start, trial_end = date.fromisoformat(cfg["trial_start"]), date.fromisoformat(cfg["trial_end"])
    if args.asof > trial_end:
        parser.error("Trial has ended; no further decisions in this version")
    folder = ROOT/"state/paper-trial/snapshots"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder/f"{args.asof}.json"
    if destination.exists():
        print(f"Snapshot already frozen: {destination}; not overwritten")
        return
    report = json.loads((ROOT/"state/research-results.json").read_text())
    if report["asof"] != str(args.asof) or report["strategy"] != cfg:
        parser.error("Run today's verified research report with the frozen config first")
    series = {s: load_bars(ROOT/f"state/market-data/{s}.json", args.asof)[0] for s in cfg["symbols"]}
    frozen = {}
    for path in sorted(folder.glob("*.json")):
        prior = json.loads(path.read_text())
        if prior["config_sha256"] != config_hash:
            parser.error("Strategy changed during trial; preserve this trial and start a separately versioned one")
        if prefix_hash(series, date.fromisoformat(prior["asof"])) != prior["price_history_sha256"]:
            parser.error("Historical inputs changed since a frozen snapshot; review corrections before replay")
        frozen[prior["asof"]] = prior["next_session_signals"]
    if args.asof < trial_start:
        state = {"starting_capital": Decimal(cfg["paper_capital"]), "cash": Decimal(cfg["paper_capital"]),
                 "ending_equity": Decimal(cfg["paper_capital"]), "net": Decimal(0),
                 "open_position": None, "trades": [], "halted_at_loss_limit": False}
    else:
        state = run_backtest(series, cfg, trial_start, args.asof, liquidate_end=False, frozen_signals=frozen)
    signals = report["signals"]
    if state["open_position"] or state["halted_at_loss_limit"] or args.asof >= trial_end:
        for signal in signals.values():
            signal["eligible"] = False
            signal["reasons"].append("existing_position_or_risk_halt_or_trial_complete")
    snapshot = {"mode": "paper", "asof": str(args.asof), "recorded_at": now.isoformat(),
                "config_sha256": config_hash, "price_history_sha256": prefix_hash(series, args.asof),
                "next_session_signals": signals, "portfolio": state,
                "execution_model": "Next daily open with price cap, slippage and fees; simulated, not an executable quote",
                "trial_complete": args.asof == trial_end}
    # Exclusive create makes re-runs unable to overwrite a decision after its outcome.
    with destination.open("x") as output:
        json.dump(snapshot, output, default=str, indent=2)
        output.write("\n")
    print(json.dumps({"snapshot": str(destination), "paper_equity": state["ending_equity"],
                      "paper_net": state["net"], "open_position": state["open_position"],
                      "eligible_symbols": [s for s,p in signals.items() if p["eligible"]],
                      "trial_complete": snapshot["trial_complete"]}, default=str, indent=2))


if __name__ == "__main__":
    main()
