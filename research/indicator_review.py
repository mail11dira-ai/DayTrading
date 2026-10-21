"""Indicator review: which day-trading signals carry information at the 8:59 CT run (no look-ahead).

Rebuilds every stock-day exactly as validate.py does (only 5-minute bars completed by 09:00 CT), then tests
fixed, textbook thresholds - nothing is tuned - two ways:
  * direction - per-day spread of the next-60-min / to-close return vs QQQ (market-adjusted), in %;
  * movement  - per-day spread of the next-60-min / rest-of-day high-low range, in units of daily ATR%.
Verdicts use validate.verdict (|t| >= 2 and the same sign in both halves of the sample).

    PYTHONPATH=. python3 -m research.indicator_review [--transcript PATH] [--out backtests/indicator_review_tables.md]
"""
import argparse
import operator as O
from datetime import datetime, timedelta

from . import collect
from . import validate as V
from .analyze import CT, analyze
from .universe import symbols

KEEP = ["bias_label", "rvol", "atr_pct", "gap_atr", "vwap", "vwap_sd", "price", "rsi_5", "range_used", "sqz",
        "pattern", "adx", "pdi", "mdi", "macd_hist", "ret30", "ret20", "orb", "div", "in_play", "thin"]


def build(ds, min_prior=10):
    syms, bench = symbols("ai100")
    allsyms = bench + syms
    cache = V.Cache(ds, allsyms)
    by_day = {}
    for b in cache.five["SPY"][1]:
        t = datetime.fromisoformat(b["begins_at"].replace("Z", "+00:00")).astimezone(CT)
        if 510 <= t.hour * 60 + t.minute < 900:
            by_day.setdefault(t.date(), []).append(t)
    days = sorted(d for d, v in by_day.items() if len(v) == 78)[min_prior:]
    at = lambda d, h, m: datetime(d.year, d.month, d.day, h, m, tzinfo=CT).astimezone(V.UTC).strftime(V.FMT)
    out = []
    for d in days:
        cut = at(d, 8, 55)
        start = (datetime(d.year, d.month, d.day, tzinfo=CT) - timedelta(days=V.HIST_DAYS)).astimezone(V.UTC).strftime(V.FMT)
        view = V.AsOf(cache, cut, start)
        res = {s: analyze(view, s, "intraday", d, datetime(d.year, d.month, d.day, 9, 0, tzinfo=CT)) for s in allsyms}
        fwd = {}
        for s in allsyms:
            p0 = next((float(b["close_price"]) for b in cache.slice(s, cut, cut)), None)
            bars = cache.slice(s, at(d, 14, 55), at(d, 9, 0))
            h60 = [b for b in bars if b["begins_at"] <= at(d, 9, 55)]
            if p0 and len(h60) >= 10:
                hl = lambda bs: (max(float(b["high_price"]) for b in bs) - min(float(b["low_price"]) for b in bs)) / p0 * 100
                fwd[s] = (p0, float(h60[-1]["close_price"]), float(bars[-1]["close_price"]), hl(h60), hl(bars))
        if "QQQ" not in fwd:
            continue
        qp0, q60, qc = fwd["QQQ"][:3]
        for s in syms:
            r = res[s]
            if not r.get("ok") or s not in fwd:
                continue
            p0, c60, cc, rng60, rngc = fwd[s]
            row = {k: r.get(k) for k in KEEP}
            a = r.get("atr_pct")
            row.update(day=d, sym=s, adj60=(c60 / p0 - q60 / qp0) * 100, adjc=(cc / p0 - qc / qp0) * 100,
                       rr60=rng60 / a if a else None, rrc=rngc / a if a else None,
                       z=(r["price"] - r["vwap"]) / r["vwap_sd"] if r.get("vwap") and r.get("vwap_sd") else None,
                       sq=r["sqz"][0] if r.get("sqz") else None, orbs=(r.get("orb") or {}).get("state"),
                       orbd=(r.get("orb") or {}).get("dir"))
            out.append(row)
    _terciles(out, ("ret20", "ret30", "rvol"))
    return out, days


def _terciles(rows, keys):
    by = {}
    for r in rows:
        by.setdefault(r["day"], []).append(r)
    for k in keys:
        for day_rows in by.values():
            v = sorted(r[k] for r in day_rows if r.get(k) is not None)
            if len(v) < 9:
                continue
            lo, hi = v[len(v) // 3], v[2 * len(v) // 3]
            for r in day_rows:
                x = r.get(k)
                r[k + "_t"] = None if x is None else (1 if x >= hi else -1 if x <= lo else 0)


def _is(k, op, v):
    return lambda r: r.get(k) is not None and op(r[k], v)


def _eq(k, v):
    return lambda r: r.get(k) == v


DIRECTION = [
    ("VWAP -2 sigma vs +2 sigma (mean reversion)", _is("z", O.le, -2), _is("z", O.ge, 2), "adj60", 1),
    ("VWAP below -1 sigma vs above +1 sigma (mean reversion)", _is("z", O.le, -1), _is("z", O.ge, 1), "adj60", 1),
    ("RSI 5m < 30 vs > 70 (mean reversion)", _is("rsi_5", O.lt, 30), _is("rsi_5", O.gt, 70), "adj60", 1),
    ("Gap up vs down >= 0.5 ATR (continuation, 60m)", _is("gap_atr", O.ge, 0.5), _is("gap_atr", O.le, -0.5), "adj60", 1),
    ("Gap up vs down >= 0.5 ATR (fade by the close)", _is("gap_atr", O.ge, 0.5), _is("gap_atr", O.le, -0.5), "adjc", -1),
    ("20-day momentum, top vs bottom third (60m)", _eq("ret20_t", 1), _eq("ret20_t", -1), "adj60", 1),
    ("20-day momentum, top vs bottom third (to close)", _eq("ret20_t", 1), _eq("ret20_t", -1), "adjc", 1),
    ("First-30-min move, top vs bottom third (to close)", _eq("ret30_t", 1), _eq("ret30_t", -1), "adjc", 1),
    ("5m MACD histogram > 0 vs < 0", _is("macd_hist", O.gt, 0), _is("macd_hist", O.lt, 0), "adj60", 1),
    ("ADX >= 25 with +DI > -DI vs -DI > +DI", lambda r: (r["adx"] or 0) >= 25 and r["pdi"] > r["mdi"],
     lambda r: (r["adx"] or 0) >= 25 and r["pdi"] < r["mdi"], "adj60", 1),
    ("5m RSI divergence bullish vs bearish", _eq("div", "bullish"), _eq("div", "bearish"), "adj60", 1),
    ("Squeeze fired up vs fired down", _eq("sq", "fired up"), _eq("sq", "fired down"), "adj60", 1),
    ("ORB confirmed up vs down (to close)", lambda r: r["orbs"] == "confirmed" and r["orbd"] == "up",
     lambda r: r["orbs"] == "confirmed" and r["orbd"] == "down", "adjc", 1),
    ("Bias BULLISH vs BEARISH (to close)", _eq("bias_label", "BULLISH"), _eq("bias_label", "BEARISH"), "adjc", 1),
]
MOVEMENT = [
    ("RVOL top vs bottom third (next 60 min)", _eq("rvol_t", 1), _eq("rvol_t", -1), "rr60", 1),
    ("RVOL top vs bottom third (rest of day)", _eq("rvol_t", 1), _eq("rvol_t", -1), "rrc", 1),
    ("|gap| >= 0.5 ATR vs < 0.2 ATR (rest of day)", lambda r: abs(r["gap_atr"] or 0) >= 0.5,
     lambda r: r["gap_atr"] is not None and abs(r["gap_atr"]) < 0.2, "rrc", 1),
    ("Range used >= 1 ATR vs < 0.5 (next 60 min)", _is("range_used", O.ge, 1.0), _is("range_used", O.lt, 0.5), "rr60", 1),
    ("ORB confirmed (either way) vs inside the range (next 60 min)", _eq("orbs", "confirmed"), _eq("orbs", "inside"), "rr60", 1),
    ("Squeeze ON vs off (next 60 min)", _eq("sq", "on"), _eq("sq", "off"), "rr60", 1),
    ("Inside day / NR7 vs none (rest of day)", lambda r: bool(r.get("pattern")), lambda r: not r.get("pattern"), "rrc", 1),
    ("In-play score >= 2 vs 0 (next 60 min)", _is("in_play", O.ge, 2), _eq("in_play", 0), "rr60", 1),
    ("In-play score >= 2 vs 0 (rest of day)", _is("in_play", O.ge, 2), _eq("in_play", 0), "rrc", 1),
]


def table(tests, rows):
    f = lambda x, d=2: "n/a" if x is None else f"{x:+.{d}f}"
    out = ["| Test | days | mean spread | t | % days > 0 | 1st half | 2nd half | verdict |", "|---|---|---|---|---|---|---|---|"]
    for name, pos, neg, key, expect in tests:
        v = V.verdict(V.day_spread([r for r in rows if r.get(key) is not None], pos, neg, key=key), expect)
        out.append(f"| {name} | {v['n']} | {f(v['mean'])} | {f(v['t'], 1)} | "
                   f"{'n/a' if v['pos'] is None else round(v['pos'])}% | {f(v['h1'])} | {f(v['h2'])} | {v['verdict']} |")
    return "\n".join(out)


def buckets(rows):
    out = ["| In-play score | stock-days | next-60-min range (x daily ATR) | rest-of-day range (x daily ATR) |", "|---|---|---|---|"]
    for k in range(5):
        g = [r for r in rows if min(r.get("in_play") or 0, 3) == min(k, 3) and r["rr60"] is not None]
        if k == 4 or not g:
            continue
        out.append(f"| {k}{'+' if k == 3 else ''} | {len(g)} | {sum(r['rr60'] for r in g) / len(g):.2f} | "
                   f"{sum(r['rrc'] for r in g) / len(g):.2f} |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transcript")
    ap.add_argument("--out", default="backtests/indicator_review_tables.md")
    a = ap.parse_args(argv)
    ds = collect.Dataset()
    collect.load_transcript(a.transcript or collect.latest_transcript(), ds)
    rows, days = build(ds)
    md = (f"# Indicator review tables (generated)\n\n{len(days)} sessions ({days[0]} -> {days[-1]}), {len(rows):,} stock-days, "
          "AI Sectors 100, as of 09:00 CT.\n\n## Direction (market-adjusted return spread, % per day)\n\n"
          + table(DIRECTION, rows) + "\n\n## Movement (range spread, x daily ATR)\n\n" + table(MOVEMENT, rows)
          + "\n\n## In-play score buckets\n\n" + buckets(rows) + "\n")
    with open(a.out, "w") as fh:
        fh.write(md)
    print(md)


if __name__ == "__main__":
    main()
