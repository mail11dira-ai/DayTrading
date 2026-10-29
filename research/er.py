"""ER agent: today's earnings reporters, scored like a quant desk would - research only, no orders.

Four stages, each printing the read-only Robinhood calls for the next one (the symbols depend on today's calendar):
  calendar -> screen (daily bars for every large-cap reporter) -> detail (quotes, analyst ratings,
  8-quarter EPS history and 2-year daily bars for the most liquid names) -> report (HTML email).

The score is a fixed-weight checklist (nothing tuned, NOT validated out of sample). Earnings direction is close
to a coin flip; the email says so. Factors (points):
  reaction  only after the report (BMO names): move since the prior close, in daily-ATR units
            >= 1.0 -> 3, >= 0.5 -> 2, >= 0.2 -> 1 (same negative)
  surprise  EPS actual vs estimate >= +5% -> 1, <= -5% -> -1
  beats     share of the last 8 reports that beat the estimate >= 75% -> 1, <= 40% -> -1
  history   share of the last 8 reports followed by an up day >= 75% -> 1, <= 25% -> -1
  momentum  20-day return vs SPY > +5% -> 1, < -5% -> -1
  trend     close vs 50-day average above -> 1, below -> -1
  analysts  buy >= 70% and target >= 10% above price -> 1; buy < 40% or target below price -> -1
Label: total >= 2 Bullish, <= -2 Bearish, else Neutral. Top 5 by |total|, then $ volume.
"""
import argparse
import json
import statistics as st
from datetime import date, datetime, timedelta
from html import escape

from . import collect, render as R
from .analyze import CT, now_ct
from .plan import P, chunks

MIN_PRICE, MIN_DVOL = 10.0, 3e8  # liquid enough to day-trade: >= $10 and >= $300M traded per day (20-day average)
DETAIL_N = 15                    # names that get the detailed (per-symbol) calls
TOP_N = 5


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def session_day(now):
    """The report day to analyse: today, or the next weekday when run after 4 pm CT or on a weekend
    (a late-evening or weekend run is preparing for the next session)."""
    d = now.date() + timedelta(days=1 if now.hour >= 16 else 0)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def reporters(ds, today):
    """{sym: entry} for today's calendar entries (one per symbol; OTC ADRs with no bars drop out later)."""
    out = {}
    for e in ds.earnings:
        rep = e.get("report") or {}
        if rep.get("date") == str(today) and e.get("symbol"):
            out.setdefault(e["symbol"], e)
    return out


def history(ds, sym, today):
    """Past reports (before today) for sym, oldest first, de-duplicated by (year, quarter)."""
    seen = {}
    for e in ds.earnings:
        rep = e.get("report") or {}
        if e.get("symbol") == sym and rep.get("date") and rep["date"] < str(today):
            seen[(e.get("year"), e.get("quarter"))] = e
    return sorted(seen.values(), key=lambda e: e["report"]["date"])[-8:]


def _daily(ds, sym, today):
    out = []
    for b in ds.series(sym, "day"):
        d = b["begins_at"][:10]
        if d < str(today) and "close_price" in b:
            out.append((d, _f(b["open_price"]), _f(b["high_price"]), _f(b["low_price"]), _f(b["close_price"]), _f(b["volume"]) or 0))
    return out


def liquidity(ds, sym, today):
    d = _daily(ds, sym, today)
    if len(d) < 20:
        return None
    return d[-1][4], st.mean(x[4] * x[5] for x in d[-20:])


def _price(q):
    """Latest price from a quote: whichever of regular / extended-hours trade is more recent."""
    quote = q.get("quote", {})
    a, b = quote.get("venue_last_trade_time") or "", quote.get("venue_last_non_reg_trade_time") or ""
    p = quote.get("last_non_reg_trade_price") if b > a else quote.get("last_trade_price")
    return _f(p), _f(quote.get("adjusted_previous_close"))


def score(ds, sym, entry, today):
    d = _daily(ds, sym, today)
    if len(d) < 21:
        return None
    close = d[-1][4]
    tr = [max(d[i][2], d[i - 1][4]) - min(d[i][3], d[i - 1][4]) for i in range(1, len(d))]
    atr_pct = st.mean(tr[-14:]) / close * 100
    pts, why = {}, {}
    timing = (entry.get("report") or {}).get("timing")
    est, act = _f((entry.get("eps") or {}).get("estimate")), _f((entry.get("eps") or {}).get("actual"))
    # reaction (only once the company has reported: BMO names at a pre-open run)
    gap = None
    q = ds.quotes.get(sym)
    if q and timing == "am":
        px, prev = _price(q)
        if px and prev:
            gap = (px / prev - 1) * 100
            g = gap / atr_pct if atr_pct else 0
            pts["reaction"] = (3 if g >= 1 else 2 if g >= 0.5 else 1 if g >= 0.2 else
                               -3 if g <= -1 else -2 if g <= -0.5 else -1 if g <= -0.2 else 0)
            why["reaction"] = f"{gap:+.1f}% since prior close ({g:+.1f} ATR)"
    surprise = None
    if est is not None and act is not None and est != 0:
        surprise = (act - est) / abs(est) * 100
        pts["surprise"] = 1 if surprise >= 5 else -1 if surprise <= -5 else 0
        why["surprise"] = f"EPS {act:.2f} vs {est:.2f} ({surprise:+.0f}%)"
    hist = [e for e in history(ds, sym, today) if _f(e["eps"].get("actual")) is not None and _f(e["eps"].get("estimate")) is not None]
    beat = None
    if len(hist) >= 4:
        beat = sum(_f(e["eps"]["actual"]) > _f(e["eps"]["estimate"]) for e in hist) / len(hist)
        pts["beats"] = 1 if beat >= 0.75 else -1 if beat <= 0.40 else 0
        why["beats"] = f"beat {sum(_f(e['eps']['actual']) > _f(e['eps']['estimate']) for e in hist)}/{len(hist)}"
    # how the stock traded after past reports: am -> that day's open-to-prior-close and close; pm -> next day
    moves = []
    idx = {x[0]: i for i, x in enumerate(d)}
    for e in hist:
        rd = e["report"]["date"]
        i = idx.get(rd)
        if i is None:
            continue
        j = i if e["report"].get("timing") == "am" else i + 1
        if 0 < j < len(d):
            moves.append((d[j][4] / d[j - 1][4] - 1) * 100)
    up = avg_move = None
    if len(moves) >= 4:
        up = sum(m > 0 for m in moves) / len(moves)
        avg_move = st.mean(abs(m) for m in moves)
        pts["history"] = 1 if up >= 0.75 else -1 if up <= 0.25 else 0
        why["history"] = f"up after {sum(m > 0 for m in moves)}/{len(moves)} reports, avg move {avg_move:.1f}%"
    spy = _daily(ds, "SPY", today)
    r20 = (close / d[-21][4] - 1) * 100
    s20 = (spy[-1][4] / spy[-21][4] - 1) * 100 if len(spy) >= 21 else 0
    rel = r20 - s20
    pts["momentum"] = 1 if rel > 5 else -1 if rel < -5 else 0
    why["momentum"] = f"20d {rel:+.1f}% vs SPY"
    if len(d) >= 50:
        sma50 = st.mean(x[4] for x in d[-50:])
        pts["trend"] = 1 if close > sma50 else -1
        why["trend"] = f"{(close / sma50 - 1) * 100:+.1f}% vs 50d avg"
    a = ds.ratings.get(sym)
    if a:
        nb, nh, ns = (int(_f(a.get(k)) or 0) for k in ("num_buy_ratings", "num_hold_ratings", "num_sell_ratings"))
        pt = _f(a.get("mean_price_target"))
        if nb + nh + ns and pt:
            buy = nb / (nb + nh + ns)
            upside = (pt / close - 1) * 100
            pts["analysts"] = 1 if buy >= 0.7 and upside >= 10 else -1 if buy < 0.4 or upside < 0 else 0
            why["analysts"] = f"{buy:.0%} buy, target {upside:+.0f}%"
    total = sum(pts.values())
    label = "BULLISH" if total >= 2 else "BEARISH" if total <= -2 else "NEUTRAL"
    return {"sym": sym, "timing": timing, "reported": act is not None or "reaction" in pts, "total": total,
            "label": label, "pts": pts, "why": why, "atr_pct": atr_pct, "gap": gap, "surprise": surprise,
            "est": est, "act": act, "beat": beat, "up": up, "avg_move": avg_move, "price": close}


# ---------------------------------------------------------------- calls per stage
def calls_calendar(today):
    return [(P + "get_earnings_calendar", {"days": 1, "filter": "high_market_cap", "start_date": str(today)})]


def calls_screen(ds, today):
    syms = sorted(reporters(ds, today)) + ["SPY"]
    start = f"{today - timedelta(days=130)}T00:00:00Z"
    return [(P + "get_equity_historicals", {"symbols": c, "interval": "day", "start_time": start}) for c in chunks(syms, 10)]


def shortlist(ds, today, n=DETAIL_N):
    rows = []
    for s in reporters(ds, today):
        liq = liquidity(ds, s, today)
        if liq and liq[0] >= MIN_PRICE and liq[1] >= MIN_DVOL:
            rows.append((s, liq[1]))
    return [s for s, _ in sorted(rows, key=lambda x: -x[1])[:n]]


def calls_detail(ds, today):
    syms = shortlist(ds, today)
    if not syms:
        return []
    calls = [(P + "get_equity_quotes", {"symbols": syms}),
             (P + "get_equity_analyst_ratings", {"symbols": syms})]
    start = f"{today - timedelta(days=800)}T00:00:00Z"  # 8 quarters of report-day moves
    calls += [(P + "get_equity_historicals", {"symbols": c, "interval": "day", "start_time": start}) for c in chunks(syms, 10)]
    calls += [(P + "get_earnings_results", {"symbol": s}) for s in syms]
    return calls


# ---------------------------------------------------------------- report
def _label(r):
    return {"BULLISH": '<span class="g">Bullish</span>', "BEARISH": '<span class="r">Bearish</span>'}.get(r["label"], "Neutral")


def build(ds, now, test=False):
    today = session_day(now)
    rep = reporters(ds, today)
    short = shortlist(ds, today)
    scored = [x for x in (score(ds, s, rep[s], today) for s in short) if x]
    scored.sort(key=lambda r: (-abs(r["total"]), short.index(r["sym"])))
    top = scored[:TOP_N]
    title = f"{'[TEST] ' if test else ''}ER Research - {now:%Y-%m-%d %H:%M} CT"
    am = sum(1 for e in rep.values() if (e.get("report") or {}).get("timing") == "am")
    note = (f"{len(rep)} large-cap companies report on {today} ({am} before the open, {len(rep) - am} after the close or unknown); "
            f"{len(short)} pass the liquidity screen (price >= ${MIN_PRICE:.0f}, >= ${MIN_DVOL / 1e6:.0f}M/day) and are scored.")
    rows = []
    for i, r in enumerate(top, 1):
        when = "BMO, reported" if r["timing"] == "am" and r["reported"] else "BMO" if r["timing"] == "am" else "AMC tonight" if r["timing"] == "pm" else "time n/a"
        rows.append([i, f"<b>{r['sym']}</b>", when, _label(r), f"{r['total']:+d}",
                     R.pct(r["gap"], 1) if r["gap"] is not None else "n/a",
                     f"{r['est']:.2f}" if r["est"] is not None else "n/a",
                     f"{r['act']:.2f} ({r['surprise']:+.0f}%)" if r["surprise"] is not None else "not yet",
                     f"{r['beat']:.0%}" if r["beat"] is not None else "n/a",
                     f"&plusmn;{r['avg_move']:.1f}%" if r["avg_move"] is not None else "n/a",
                     f"{r['atr_pct']:.1f}%"])
    body = "<h3>1. Top 5 earnings names today</h3>"
    body += (R.table(["#", "Stock", "Report", "Call", "Score", "Move", "EPS est", "EPS actual", "Beat rate (8q)",
                      "Avg ER move", "ATR"], rows, left=3, tint=3) if rows else "<p>No liquid large-cap reporters today.</p>")
    body += "<h3>2. Why</h3><ul>" + "".join(
        f"<li><b>{r['sym']}</b> {_label(r)} ({r['total']:+d}): "
        + "; ".join(f"{k} {r['pts'][k]:+d} ({escape(r['why'][k])})" for k in r["pts"]) + "</li>" for r in top) + "</ul>"
    rest = scored[TOP_N:]
    if rest:
        body += "<h3>3. Rest of the screened list</h3><p>" + ", ".join(f"{r['sym']} {_label(r)} {r['total']:+d}" for r in rest) + "</p>"
    body += ("<h3>Method</h3><p>Fixed-weight checklist, nothing tuned: reaction since the prior close in ATR units (reported names only, "
             "up to &plusmn;3), EPS surprise (&plusmn;1), 8-quarter beat rate (&plusmn;1), up-day rate after past reports "
             "(&plusmn;1), 20-day return vs SPY (&plusmn;1), price vs 50-day average (&plusmn;1), analyst buy share and "
             "target (&plusmn;1). Score &ge; +2 Bullish, &le; -2 Bearish. <b>Not validated out of sample</b>: post-earnings "
             "direction is close to a coin flip, and names reporting after the close (AMC) have no reaction yet, so their "
             "call rests on history only. Size positions for the average earnings move shown.</p>")
    missing = [s for s in short if s not in {r["sym"] for r in scored}]
    return title, R.doc(title, note, body), missing, scored


def main(argv=None):
    ap = argparse.ArgumentParser(description="ER agent: today's earnings reporters, research only")
    ap.add_argument("stage", choices=["calendar", "screen", "detail", "report"])
    ap.add_argument("--transcript")
    ap.add_argument("--data", help="directory of raw tool-result JSON files")
    ap.add_argument("--now", help="override current time (ISO, CT if no offset)")
    ap.add_argument("--out", default="/tmp/er_report.html")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args(argv)
    now = now_ct(a.now)
    ds = collect.Dataset()
    if a.data:
        collect.load_dir(a.data, ds)
    if a.transcript or not a.data:
        path = a.transcript or collect.latest_transcript()
        if path:
            collect.load_transcript(path, ds)
    if a.stage != "report":
        day = session_day(now)
        calls = {"calendar": lambda: calls_calendar(day), "screen": lambda: calls_screen(ds, day),
                 "detail": lambda: calls_detail(ds, day)}[a.stage]()
        for tool, args in calls:
            print(json.dumps({"tool": tool, "args": args}))
        return
    from .report import _write_parts
    title, html, missing, scored = build(ds, now, a.test)
    with open(a.out, "w") as f:
        f.write(html)
    parts = _write_parts(a.out, html.replace("</li>", "</li>\n").replace("</table>", "</table>\n"), 24000)
    print(json.dumps({"subject": title, "parts": parts, "bytes": len(html), "scored": len(scored), "missing": missing}))


if __name__ == "__main__":
    main()
