"""Nodes N4/N6: run a strategy on train and test windows and write a markdown report.

Usage: python -m src.evaluate <name> [--test]
Without --test only the train window runs (for tuning). With --test the test window is
evaluated too; per CLAUDE.md that is done once per iteration.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src import metrics
from src.backtest import Config, run, split_sessions
from src.data import load

TRAIN_FRAC = 0.7


def buy_and_hold(bars: pd.DataFrame, symbol: str = "SPY", equity0: float = 25_000.0) -> pd.Series:
    """Equity of buying `symbol` at the first open and holding (no costs)."""
    b = bars[bars["symbol"] == symbol].sort_values("timestamp")
    return pd.Series(equity0 * b["close"].to_numpy() / b["open"].iloc[0],
                     index=pd.DatetimeIndex(b["timestamp"]), name="equity")


def evaluate(bars: pd.DataFrame, strategy, config: Config | None = None) -> dict:
    res = run(bars, strategy, config)
    s = metrics.summary(res.equity, res.trades)
    s["rejected_signals"] = len(res.rejected)
    s["sessions"] = bars["timestamp"].dt.date.nunique()
    return {"summary": s, "result": res}


def fmt_row(name: str, s: dict) -> str:
    pf = s["profit_factor"]
    return (f"| {name} | {s['total_return']:+.2%} | {s['sharpe']:.2f} | {s['max_drawdown']:.2%} | "
            f"{s['n_trades']} | {s['win_rate']:.1%} | {'inf' if pf == float('inf') else f'{pf:.2f}'} | "
            f"{s['avg_trade_pnl']:+.2f} |")


HEADER = ("| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |\n"
          "|---|---|---|---|---|---|---|---|")


def window_label(bars: pd.DataFrame) -> str:
    d = bars["timestamp"].dt.date
    return f"{d.min()} → {d.max()} ({d.nunique()} sessions)"


def bh_summary(bars: pd.DataFrame) -> dict:
    eq = buy_and_hold(bars)
    return metrics.summary(eq, pd.DataFrame({"pnl": [eq.iloc[-1] - eq.iloc[0]]}))


def report(title: str, strategies: dict, include_test: bool, notes: str = "") -> str:
    bars = load()
    train, test = split_sessions(bars, TRAIN_FRAC)
    windows = [("train", train)] + ([("test", test)] if include_test else [])
    lines = [f"# {title}", "", notes, "",
             "Config: $25,000 start, slippage 0.02%/side, $0 commission, risk limits from `src/risk.py` defaults.",
             ""]
    for wname, wbars in windows:
        lines += [f"## {wname}: {window_label(wbars)}", "", HEADER,
                  fmt_row("SPY buy & hold", bh_summary(wbars))]
        for sname, strat in strategies.items():
            out = evaluate(wbars, strat)
            lines.append(fmt_row(sname, out["summary"]))
            exits = out["result"].trades["exit_reason"].value_counts().to_dict()
            lines.append(f"<!-- {sname} exits: {exits}; rejected: {out['summary']['rejected_signals']} -->")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from src.strategies.orb import ORB
    name = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    text = report("Baseline", {"ORB 30m (default)": ORB()}, include_test="--test" in sys.argv)
    Path(f"backtests/{name}.md").write_text(text)
    print(text)
