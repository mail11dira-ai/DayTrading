"""Print the exact read-only Robinhood tool calls an agent run needs.

    python -m research.plan --agent mag7

One JSON object per line: {"tool": <name>, "args": {...}}. The agent issues
them as-is (in parallel) and then runs research.report, which reads the
results from the session transcript.
"""
import argparse
import json
from datetime import timedelta

from .analyze import now_ct
from .universe import ratings_symbols, symbols

P = "mcp__Robinhood_Agentic__"


def chunks(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


VIX_ID = "3b912aa2-88f9-4682-8ae3-e39520bdf4db"  # Robinhood market-index id for VIX (get_indexes)


def plan(agent, now):
    syms, bench = symbols(agent)
    allsyms = bench + syms
    today = now.date()
    # ONE extended-hours 5-minute pull (pre / regular / post bars, 10 prior sessions + today): gives the regular
    # series, today's pre-market and the prior pre-markets for pre-market RVOL.
    start5 = f"{today - timedelta(days=14)}T08:00:00Z"
    startd = f"{today - timedelta(days=400)}T00:00:00Z"
    calls = []
    for c in chunks(allsyms, 20):
        calls.append((P + "get_equity_quotes", {"symbols": c}))
    for c in chunks(allsyms, 5):
        calls.append((P + "get_equity_historicals", {"symbols": c, "interval": "5minute", "bounds": "extended", "start_time": start5}))
    for c in chunks(allsyms, 10):
        calls.append((P + "get_equity_historicals", {"symbols": c, "interval": "day", "start_time": startd}))
    calls.append((P + "get_earnings_calendar", {"days": 15, "filter": "high_market_cap"}))
    for c in chunks(ratings_symbols(agent), 75):  # tool limit: 75 symbols per call
        calls.append((P + "get_equity_analyst_ratings", {"symbols": c}))
    calls.append((P + "get_index_quotes", {"instrument_ids": [VIX_ID]}))
    if agent == "mag7":  # market deep dive: VIX history (1 year daily) and its intraday path (last few sessions)
        calls.append((P + "get_index_historicals", {"instrument_ids": [VIX_ID], "interval": "day", "start_time": startd}))
        calls.append((P + "get_index_historicals", {"instrument_ids": [VIX_ID], "interval": "5minute",
                                                     "start_time": f"{today - timedelta(days=4)}T12:00:00Z"}))
    return calls


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=["mag7", "aisectors", "modern", "ai100"])
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    for tool, args in plan(a.agent, now_ct(a.now)):
        print(json.dumps({"tool": tool, "args": args}, separators=(",", ":")))


if __name__ == "__main__":
    main()
