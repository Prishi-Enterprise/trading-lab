"""Freeze NSE-only prospective paper decisions; never route an order."""

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal

from .nse_only import ARCHIVES, completed_today, fetch_archive, load_series
from .paper import prefix_hash
from .research import ROOT, candidate, run_backtest


def main():
    parser = argparse.ArgumentParser(description="NSE-only prospective paper snapshot")
    parser.add_argument("--asof", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    now = completed_today(args.asof)
    config_bytes = (ROOT / "research-config-nse-v2.json").read_bytes()
    config_hash = hashlib.sha256(config_bytes).hexdigest()
    cfg = json.loads(config_bytes)
    start, end = date.fromisoformat(cfg["trial_start"]), date.fromisoformat(cfg["trial_end"])
    if cfg["mode"] != "paper" or not start <= args.asof <= end:
        parser.error("Date outside the frozen paper trial")
    if fetch_archive(args.asof) is None:
        parser.error("No completed NSE bhavcopy for today")
    series, provenance = load_series(ARCHIVES, args.asof)
    folder = ROOT / "state/nse-only/snapshots"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{args.asof}.json"
    if destination.exists():
        print(f"Snapshot already frozen: {destination}; not overwritten")
        return
    frozen = {}
    for path in sorted(folder.glob("*.json")):
        prior = json.loads(path.read_text())
        prior_day = date.fromisoformat(prior["asof"])
        if prior["config_sha256"] != config_hash:
            raise ValueError("Strategy changed during trial; preserve old snapshots")
        if prefix_hash(series, prior_day) != prior["price_history_sha256"]:
            raise ValueError("Earlier NSE prices changed; review before replay")
        frozen[prior["asof"]] = prior["next_session_signals"]
    if args.asof == start:
        state = {"starting_capital": Decimal(cfg["paper_capital"]),
                 "cash": Decimal(cfg["paper_capital"]),
                 "ending_equity": Decimal(cfg["paper_capital"]), "net": Decimal(0),
                 "open_position": None, "trades": [], "halted_at_loss_limit": False}
    else:
        state = run_backtest(series, cfg, date.fromisoformat(cfg["first_possible_execution"]),
                             args.asof, liquidate_end=False, frozen_signals=frozen)
    signals = {symbol: candidate(bars, len(bars)-1, cfg, Decimal(state["cash"]))
               for symbol, bars in series.items()}
    if state["open_position"] or state["halted_at_loss_limit"] or args.asof == end:
        for plan in signals.values():
            plan["eligible"] = False
            plan["reasons"].append("existing_position_or_risk_halt_or_trial_complete")
    snapshot = {"mode": "paper", "source": "NSE official bhavcopy", "asof": str(args.asof),
                "recorded_at": now.isoformat(), "config_sha256": config_hash,
                "price_history_sha256": prefix_hash(series, args.asof),
                "source_archive_sha256": provenance[-1]["sha256"],
                "next_session_signals": signals, "portfolio": state,
                "execution_model": "Next NSE daily open with cap, slippage and estimated fees; simulated only",
                "trial_complete": args.asof == end}
    with destination.open("x") as output:
        json.dump(snapshot, output, default=str, indent=2)
        output.write("\n")
    print(json.dumps({"snapshot": str(destination), "paper_equity": state["ending_equity"],
                      "paper_net": state["net"], "open_position": state["open_position"],
                      "eligible_symbols": [s for s, p in signals.items() if p["eligible"]],
                      "trial_complete": snapshot["trial_complete"]}, default=str, indent=2))


if __name__ == "__main__":
    main()
