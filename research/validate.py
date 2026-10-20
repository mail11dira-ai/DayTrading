"""Out-of-sample check of the bias score and the new day-trading signals.

For every session in the downloaded history this rebuilds the analysis exactly as the 8:59 CT run would have
seen it (only 5-minute bars that had completed by 09:00 CT, no look-ahead), then compares each signal with what
the stock did over the next 60 minutes and to the close. Returns are market-adjusted (stock minus QQQ over the
same window) so a rising tape does not flatter bullish signals.

Per-day cross-sectional spreads are used (e.g. mean return of BULLISH stocks minus BEARISH stocks on that day),
and significance is judged across days, because stocks on one day move together. Rules are measured as they are:
nothing here is tuned on the data.

    python3 -m research.validate [--transcript PATH] [--out backtests/bias_validation.md]
"""
import argparse
import bisect
import gzip
import json
import math
import os
from datetime import datetime, timedelta, timezone

from . import collect
from .analyze import CT, analyze
from .universe import symbols

UTC = timezone.utc
FMT = "%Y-%m-%dT%H:%M:%SZ"
HIST_DAYS = 18  # the analysis only needs ~10 prior sessions of 5-minute bars


class Cache:
    """Sorted 5-minute bar lists per symbol for fast as-of slicing."""

    def __init__(self, ds, syms):
        self.ds = ds
        self.five = {}
        for s in syms:
            bars = ds.series(s, "5minute")
            self.five[s] = ([b["begins_at"] for b in bars], bars)

    def slice(self, sym, cut_iso, start_iso):
        keys, bars = self.five[sym]
        return bars[bisect.bisect_left(keys, start_iso):bisect.bisect_right(keys, cut_iso)]


class AsOf:
    """Dataset view as of one clock time: completed 5-minute bars only, no live quotes."""

    def __init__(self, cache, cut, start):
        self.cache, self.cut, self.start = cache, cut, start
        self.quotes = {}

    def series(self, sym, interval):
        if interval == "5minute":
            return self.cache.slice(sym, self.cut, self.start)
        return self.cache.ds.series(sym, interval)


def tstat(xs):
    n = len(xs)
    if n < 3:
        return None
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m / (sd / math.sqrt(n)) if sd else None


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def day_spread(samples, pos, neg, key="adj60", min_side=2):
    """{day: mean(key | pos) - mean(key | neg)} for days with at least min_side samples on each side."""
    by = {}
    for s in samples:
        by.setdefault(s["day"], []).append(s)
    out = {}
    for d, rows in sorted(by.items()):
        a = [r[key] for r in rows if pos(r)]
        b = [r[key] for r in rows if neg(r)]
        if len(a) >= min_side and len(b) >= min_side:
            out[d] = mean(a) - mean(b)
    return out


def verdict(spread_by_day, expect=1):
    """Summarise a day-spread series: mean, t-stat over days, % positive days, both halves, and a verdict.

    expect = +1 when a positive spread means the signal works as designed, -1 when a negative one does.
    """
    days = sorted(spread_by_day)
    xs = [expect * spread_by_day[d] for d in days]
    if len(xs) < 6:
        return {"n": len(xs), "mean": None, "t": None, "pos": None, "h1": None, "h2": None, "verdict": "too few days"}
    h = len(xs) // 2
    t = tstat(xs)
    m1, m2 = mean(xs[:h]), mean(xs[h:])
    if t is not None and t >= 2 and m1 > 0 and m2 > 0:
        v = "supported"
    elif t is not None and t <= -2 and m1 < 0 and m2 < 0:
        v = "INVERTED"
    else:
        v = "no clear edge"
    return {"n": len(xs), "mean": mean(xs), "t": t, "pos": 100 * sum(1 for x in xs if x > 0) / len(xs),
            "h1": m1, "h2": m2, "verdict": v}


def build_samples(ds, hour_cut=(8, 55), min_prior=10):
    syms, bench = symbols("ai100")
    allsyms = bench + syms
    cache = Cache(ds, allsyms)
    spy = cache.five["SPY"][1]
    by_day = {}
    for b in spy:
        t = datetime.fromisoformat(b["begins_at"].replace("Z", "+00:00")).astimezone(CT)
        if 8 * 60 + 30 <= t.hour * 60 + t.minute < 15 * 60:
            by_day.setdefault(t.date(), []).append(t)
    days = sorted(d for d, v in by_day.items() if len(v) == 78)
    asof_days = days[min_prior:]

    def at(d, h, m):
        return datetime(d.year, d.month, d.day, h, m, tzinfo=CT).astimezone(UTC).strftime(FMT)

    samples = []
    for d in asof_days:
        cut = at(d, *hour_cut)
        start = (datetime(d.year, d.month, d.day, tzinfo=CT) - timedelta(days=HIST_DAYS)).astimezone(UTC).strftime(FMT)
        view = AsOf(cache, cut, start)
        now = datetime(d.year, d.month, d.day, 9, 0, tzinfo=CT)
        k60, kc = at(d, 9, 55), at(d, 14, 55)
        close_at = lambda sym, k: next((float(b["close_price"]) for b in cache.slice(sym, k, k)), None)
        res = {s: analyze(view, s, "intraday", d, now) for s in allsyms}
        q = res["QQQ"]
        q60, qc, q0 = close_at("QQQ", k60), close_at("QQQ", kc), close_at("QQQ", cut)
        if not (q.get("ok") and q60 and qc and q0):
            continue
        qf60, qfc = (q60 / q0 - 1) * 100, (qc / q0 - 1) * 100
        for s in syms:
            r = res[s]
            if not r["ok"]:
                continue
            p0, p60, pc = close_at(s, cut), close_at(s, k60), close_at(s, kc)
            if not (p0 and p60 and pc):
                continue
            f60, fc = (p60 / p0 - 1) * 100, (pc / p0 - 1) * 100
            rs30 = r["ret30"] - q["ret30"] if (r.get("ret30") is not None and q.get("ret30") is not None) else None
            samples.append({
                "day": d, "sym": s, "bias": r["bias"], "label": r["bias_label"], "comp": r["bias_comp"],
                "conf": r.get("conf", 0), "orb": r.get("orb"), "rs30": rs30, "rvol": r.get("rvol") or 0.0,
                "setup": r.get("setup"), "fwd60": f60, "fwdc": fc, "adj60": f60 - qf60, "adjc": fc - qfc,
                "gap_q": r.get("gap_q"), "hold": r.get("hold_821"),
            })
    return samples, asof_days


def save_samples(samples, days, path):
    """Persist the per-stock-day samples so the report can be regenerated without the raw bars."""
    def enc(x):
        if isinstance(x, (datetime,)) or hasattr(x, "isoformat"):
            return x.isoformat()
        raise TypeError(type(x))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump({"days": [d.isoformat() for d in days], "samples": samples}, f, default=enc)


def load_samples(path):
    from datetime import date
    with gzip.open(path, "rt") as f:
        d = json.load(f)
    days = [date.fromisoformat(x) for x in d["days"]]
    for s in d["samples"]:
        s["day"] = date.fromisoformat(s["day"])
        if s.get("gap_q"):
            s["gap_q"] = tuple(s["gap_q"])
    return d["samples"], days


def _fmt(x, d=2, sign=True):
    return "n/a" if x is None else (f"{x:+.{d}f}" if sign else f"{x:.{d}f}")


def report(samples, days):
    L = []
    P = L.append
    n_days = len({s["day"] for s in samples})
    P("# Bias score & signal validation\n")
    P(f"Universe: AI Sectors 100 ({len({s['sym'] for s in samples})} stocks). Sessions tested: **{n_days}** "
      f"({days[0]} -> {days[-1]}), run time 09:00 CT (the 8:59 run), {len(samples):,} stock-days. "
      "Returns are **market-adjusted** (stock minus QQQ over the same window), in %. Rules are measured as-is, not tuned.\n")
    P("How to read: a *spread* is the average return of stocks with the signal on minus stocks with the opposite signal, "
      "computed per day and judged across days (t-stat, % of days positive, first half vs second half of the sample). "
      "**supported** = t >= 2 and positive in both halves; **INVERTED** = t <= -2 and negative in both halves; otherwise "
      "**no clear edge**. With ~12 tests, one or two |t| of 2-3 can appear by chance.\n")

    # 0. how often each component fires (a component stuck at 0 can never help)
    P("## 0. Component activity at 09:00 CT (share of stock-days)\n")
    P("| Component | bullish (+1) | bearish (-1) | neutral (0) |\n|---|---|---|---|")
    for k, nm in (("vwap", "price vs VWAP"), ("ema", "5m EMA 9/21"), ("stack", "daily MA stack"), ("rsi", "5m RSI zone"),
                  ("vol", "volume"), ("struct", "intraday structure")):
        up = 100 * sum(1 for s in samples if s["comp"][k] > 0) / len(samples)
        dn = 100 * sum(1 for s in samples if s["comp"][k] < 0) / len(samples)
        P(f"| {nm} | {up:.0f}% | {dn:.0f}% | {100 - up - dn:.0f}% |")
    P("")

    # 1. bias buckets
    P("## 1. Bias score buckets\n")
    P("| Bias | N | Next 60 min: mean adj % | hit rate | To close: mean adj % |\n|---|---|---|---|---|")
    buckets = [("<= -3 BEARISH", lambda s: s["bias"] <= -3, -1), ("-2 .. -1", lambda s: -2 <= s["bias"] <= -1, -1),
               ("0", lambda s: s["bias"] == 0, 0), ("+1 .. +2", lambda s: 1 <= s["bias"] <= 2, 1),
               (">= +3 BULLISH", lambda s: s["bias"] >= 3, 1)]
    for name, f, sg in buckets:
        rows = [s for s in samples if f(s)]
        if not rows:
            P(f"| {name} | 0 | n/a | n/a | n/a |")
            continue
        hit = "n/a" if sg == 0 else f"{100 * sum(1 for r in rows if r['adj60'] * sg > 0) / len(rows):.0f}%"
        P(f"| {name} | {len(rows)} | {_fmt(mean([r['adj60'] for r in rows]))} | {hit} | {_fmt(mean([r['adjc'] for r in rows]))} |")
    P("")

    # 2. spreads
    P("## 2. Signal tests (spread of next-60-min market-adjusted return, % per day)\n")
    ctl = day_spread(samples, lambda s: s["bias"] >= 3, lambda s: s["bias"] <= -3, key="rs30")
    cv = verdict({d: x for d, x in ctl.items()})
    P(f"*Control (should be strongly positive, it is not a forecast): the trailing 30-minute move vs QQQ of BULLISH minus BEARISH "
      f"stocks averages {_fmt(cv['mean'])}% (t = {_fmt(cv['t'], 1)}) - the score does describe what the stock has just done; "
      "the tests below ask whether that continues.*\n")
    P("| Signal | days | mean spread | t | % days > 0 | 1st half | 2nd half | verdict |\n|---|---|---|---|---|---|---|---|")
    tests = [
        ("**Bias >= +3 vs <= -3** (the headline score)", lambda s: s["bias"] >= 3, lambda s: s["bias"] <= -3, 1),
        ("Bias >= +1 vs <= -1", lambda s: s["bias"] >= 1, lambda s: s["bias"] <= -1, 1),
        ("Component: price vs VWAP", lambda s: s["comp"]["vwap"] > 0, lambda s: s["comp"]["vwap"] < 0, 1),
        ("Component: 5m EMA 9 vs 21", lambda s: s["comp"]["ema"] > 0, lambda s: s["comp"]["ema"] < 0, 1),
        ("Component: daily MA stack", lambda s: s["comp"]["stack"] > 0, lambda s: s["comp"]["stack"] < 0, 1),
        ("Component: 5m RSI zone", lambda s: s["comp"]["rsi"] > 0, lambda s: s["comp"]["rsi"] < 0, 1),
        ("Component: volume (RVOL > 1.2 + up/down)", lambda s: s["comp"]["vol"] > 0, lambda s: s["comp"]["vol"] < 0, 1),
        ("Component: intraday structure", lambda s: s["comp"]["struct"] > 0, lambda s: s["comp"]["struct"] < 0, 1),
        ("ORB confirmed up vs confirmed down", lambda s: _orb(s, "confirmed", "up"), lambda s: _orb(s, "confirmed", "down"), 1),
        ("ORB failed up vs failed down (expect <0)", lambda s: _orb(s, "failed", "up"), lambda s: _orb(s, "failed", "down"), -1),
        ("Intraday RS: leading (>= +0.3%) vs lagging (<= -0.3%)", lambda s: (s["rs30"] or 0) >= 0.3, lambda s: (s["rs30"] if s["rs30"] is not None else 0) <= -0.3, 1),
        ("Holding 8/21 trend vs below EMA21", lambda s: s["hold"] == "holding", lambda s: s["hold"] == "lost", 1),
    ]
    results = {}
    for name, pos, neg, exp in tests:
        v = verdict(day_spread(samples, pos, neg), exp)
        results[name] = v
        P(f"| {name} | {v['n']} | {_fmt(v['mean'])} | {_fmt(v['t'], 1)} | "
          f"{'n/a' if v['pos'] is None else f'{v['pos']:.0f}%'} | {_fmt(v['h1'])} | {_fmt(v['h2'])} | {v['verdict']} |")
    P("")

    # 3. confirmations and top 5
    P("## 3. Confirmations and the top-5 ranking\n")
    strong = [s for s in samples if abs(s["bias"]) >= 3]
    P("Direction-adjusted return (long if bullish, short if bearish), stocks with |bias| >= 3:\n")
    P("| MACD/ADX confirmations | N | mean adj % (next 60 min) | hit rate |\n|---|---|---|---|")
    for c in (0, 1, 2):
        rows = [s for s in strong if s["conf"] == c]
        if rows:
            dr = [(1 if r["bias"] > 0 else -1) * r["adj60"] for r in rows]
            P(f"| {c} | {len(rows)} | {_fmt(mean(dr))} | {100 * sum(1 for x in dr if x > 0) / len(dr):.0f}% |")
    P("")
    top_days, all_days = [], []
    by = {}
    for s in samples:
        by.setdefault(s["day"], []).append(s)
    for d, rows in sorted(by.items()):
        cands = [r for r in rows if r["label"] != "NEUTRAL" and r["setup"] and r["setup"]["rr"] is not None and r["setup"]["rr"] >= 1.0]
        cands.sort(key=lambda r: (-abs(r["bias"]), -r["conf"], -r["rvol"], -(r["setup"]["rr"] or 0)))
        sg = lambda r: 1 if r["bias"] > 0 else -1
        if len(cands) >= 5:
            top_days.append(mean([sg(r) * r["adj60"] for r in cands[:5]]))
        if cands:
            all_days.append(mean([sg(r) * r["adj60"] for r in cands]))
    t_top, t_all = tstat(top_days), tstat(all_days)
    P(f"Top-5 setups (ranked by |bias|, confirmations, RVOL, R/R), direction-adjusted next-60-min return per day: "
      f"mean **{_fmt(mean(top_days))}%** over {len(top_days)} days (t = {_fmt(t_top, 1)}); "
      f"all qualifying setups: {_fmt(mean(all_days))}% (t = {_fmt(t_all, 1)}).\n")

    # 4. summary
    P("## 4. Summary\n")
    sup = [k for k, v in results.items() if v["verdict"] == "supported"]
    inv = [k for k, v in results.items() if v["verdict"] == "INVERTED"]
    none = [k for k, v in results.items() if v["verdict"] == "no clear edge"]
    P("- **Supported (t >= 2, both halves positive):** " + ("; ".join(sup) or "none"))
    P("- **Inverted (worked backwards):** " + ("; ".join(inv) or "none"))
    P("- **No clear edge:** " + ("; ".join(none) or "none"))
    P("\nNot testable here: pre-market volume and gap quality (needs pre-market history for every past session); "
      "they are shown in the email as context only and are **not** part of the bias score or the ranking.")
    return "\n".join(L), results, (top_days, all_days)


def _orb(s, state, d):
    o = s["orb"]
    return bool(o) and o["state"] == state and o["dir"] == d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transcript")
    ap.add_argument("--out", default="backtests/bias_validation.md")
    ap.add_argument("--samples", default="backtests/bias_validation_samples.json.gz",
                    help="where the per-stock-day samples are saved / loaded")
    ap.add_argument("--from-samples", action="store_true", help="regenerate the report from saved samples (no raw bars needed)")
    a = ap.parse_args(argv)
    if a.from_samples:
        samples, days = load_samples(a.samples)
    else:
        ds = collect.Dataset()
        collect.load_transcript(a.transcript or collect.latest_transcript(), ds)
        samples, days = build_samples(ds)
        save_samples(samples, days, a.samples)
    text, results, _ = report(samples, days)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
