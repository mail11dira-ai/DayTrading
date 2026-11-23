"""Node X5: assemble the pre-market markdown report. Code only."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from xers.config import HANDLES

DISCLAIMER = ("> **Not financial advice.** Rankings summarize what these X accounts posted; levels and "
              "entries are mechanical rules, not a tested edge. In this repo's backtest (run 1), "
              "opening-range breakouts had no out-of-sample edge; a relative-volume filter helped "
              "but did not beat SPY. Paper-trade first.")


def _p(x):
    return "—" if x is None else f"{x:,.2f}"


def _plan_line(tk: str, lv: dict | None, pl: dict | None) -> list[str]:
    if lv is None or pl is None:
        return [f"### {tk}", "", "_No Robinhood bars available — levels not computed._", ""]
    verb = "close above" if pl["side"] == "long" else "close below"
    rvol = "—" if lv["pm_rvol"] is None else f"{lv['pm_rvol']:.1f}×"
    lines = [
        f"### {tk} — {pl['side'].upper()}",
        "",
        f"Last {_p(lv['last'])} (gap {lv['gap_pct']:+.2%}) · ATR {_p(lv['atr'])} · pre-market volume "
        f"{lv['pm_volume']:,} (RVOL {rvol}) · prior session {lv['prev_date']}: "
        f"H {_p(lv['prev_high'])} / L {_p(lv['prev_low'])} / C {_p(lv['prev_close'])}",
        "",
        "| | level | price |",
        "|---|---|---|",
        f"| **Entry** | 5-min {verb} {pl['entry_level']} after 9:35 ET | {_p(pl['entry'])} |",
        f"| **Stop** | {pl['stop_level']} | {_p(pl['stop'])} |",
        f"| **Target 1** | {pl['t1_level']} (R:R {pl['rr_t1']:.1f}) | {_p(pl['t1'])} |",
        f"| **Target 2** | {pl['t2_level']} | {_p(pl['t2'])} |",
        f"| Size | 1% risk on $25k (`src/risk.py`) | {pl['shares']} sh |",
        "",
        "Support: " + ", ".join(f"{k} {_p(v)}" for k, v in pl["supports"]) +
        " · Resistance: " + ", ".join(f"{k} {_p(v)}" for k, v in pl["resistances"]),
        "",
        "Exit: half at T1 and move stop to entry; rest at T2 or flat by 15:55 ET. "
        "Skip if not triggered by 11:00 ET, or if relative volume is below 1.0× at entry.",
    ]
    if pl["rr_t1"] < 1.0:
        lines.append("")
        lines.append("⚠️ **R:R to T1 below 1.0 — low-quality setup, consider skipping.**")
    return lines + [""]


def _table(rows: list[dict]) -> list[str]:
    if not rows:
        return ["_None._", ""]
    out = ["| # | ticker | score | handles agreeing | handles against | mentions |",
           "|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        out.append(f"| {i} | **{r['ticker']}** | {r['score']:+.2f} | "
                   f"{', '.join('@' + h for h in r['handles_agree'])} | "
                   f"{', '.join('@' + h for h in r['handles_disagree']) or '—'} | {r['mentions']} |")
    return out + [""]


def build(trade_date, start: datetime, end: datetime, tweets: list[dict], ranking: dict,
          levels: dict, plans: dict, label_source: str, fetch_errors: dict, sample: bool = False) -> str:
    per_handle = Counter(t["handle"].lower() for t in tweets)
    silent = [h for h in HANDLES if per_handle[h.lower()] == 0]
    title = f"# Xers Stocks Analysis — {trade_date}"
    if sample:
        title += " (SAMPLE INPUT — not real posts)"
    lines = [title, "", DISCLAIMER, "",
             f"Window: {start:%a %Y-%m-%d %H:%M} → {end:%a %Y-%m-%d %H:%M} ET · "
             f"{len(tweets)} posts from {len(HANDLES) - len(silent)}/{len(HANDLES)} accounts · "
             f"stance labels: {label_source}", ""]
    if silent:
        lines += [f"No posts in window: {', '.join('@' + h for h in silent)}", ""]
    if fetch_errors:
        lines += ["Fetch errors: " + "; ".join(f"@{h}: {e}" for h, e in fetch_errors.items()), ""]

    lines += ["## Top bullish", ""] + _table(ranking["bullish"])
    lines += ["## Top bearish", ""] + _table(ranking["bearish"])
    lines += ["## Trade plans", ""]
    for side in ("bullish", "bearish"):
        for r in ranking[side]:
            lines += _plan_line(r["ticker"], levels.get(r["ticker"]), plans.get(r["ticker"]))

    by_id = {t["id"]: t for t in tweets}
    lines += ["## Supporting posts", ""]
    for side in ("bullish", "bearish"):
        for r in ranking[side]:
            lines.append(f"**{r['ticker']}**")
            for tid in r["tweet_ids"][:4]:
                t = by_id[tid]
                text = " ".join(t["text"].split())
                snippet = text[:200] + ("…" if len(text) > 200 else "")
                link = f" ([link]({t['url']}))" if t.get("url") else ""
                lines.append(f"- @{t['handle']}: {snippet}{link}")
            lines.append("")
    return "\n".join(lines)
