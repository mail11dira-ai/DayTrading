"""ER agent: earnings reporters, scored like a quant desk would - research only, no orders.

Four stages, each printing the read-only Robinhood calls for the next one (the symbols depend on the calendar):
  calendar -> screen (daily bars for every reporter in scope) -> detail (quotes, analyst ratings,
  8-quarter EPS history and 2-year daily bars for the most traded names) -> report (HTML email).

Which reporters are in scope depends on the run time (CT):
  morning run (before noon)   today's before-the-open (BMO) and after-the-close (AMC) reporters
  afternoon run (noon onward) today's AMC reporters and the next session's BMO reporters (today's BMO have already reported)

The score is a fixed-weight checklist (nothing tuned, NOT validated out of sample). Earnings direction is close
to a coin flip; the email says so. Factors (points):
  reaction  only after the report (BMO names already reported): move since the prior close, in daily-ATR units
            >= 1.0 -> 3, >= 0.5 -> 2, >= 0.2 -> 1 (same negative)
  surprise  EPS actual vs estimate >= +5% -> 1, <= -5% -> -1
  beats     share of the last 8 reports that beat the estimate >= 75% -> 1, <= 40% -> -1
  history   share of the last 8 reports followed by an up day >= 75% -> 1, <= 25% -> -1
  momentum  20-day return vs SPY > +5% -> 1, < -5% -> -1
  trend     close vs 50-day average above -> 1, below -> -1
  analysts  buy >= 70% and target >= 10% above price -> 1; buy < 40% or target below price -> -1
Label: total >= 2 Bullish, <= -2 Bearish, else Neutral. The email shows the top 5 Bullish and top 5 Bearish
among the most traded names in scope (DETAIL_N by dollar volume), ranked by |total| then dollar volume.
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
MIN_SHARES = 2e6                 # high-volume shares: >= 2M shares traded per day (20-day average)
MIN_ATR = 1.5                    # technical: daily ATR14 >= 1.5% of price, enough movement to trade
RSI_BAND = (25, 75)              # technical: RSI14 inside 25-75, not already stretched
MAX_PRIOR_MOVE = 10.0            # context: prior session moved <= 10%, so the news is not already priced in
DETAIL_N = 20                    # "popular" = the 20 most traded screened names; they get the detailed calls
TOP_N = 5                        # setups per side (Bullish / Bearish) in each email


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


def plan(now):
    """(report day, [(date, timing), ...]) for this run.
    Morning (before noon CT): today's BMO and AMC. Afternoon: today's AMC and the next session's BMO."""
    day = session_day(now)
    if now.hour < 12:
        return day, [(day, "am"), (day, "pm")]
    nxt = day + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return day, [(day, "pm"), (nxt, "am")]


def candidates(ds, slots):
    """{sym: (calendar entry, report date, timing)} for the reporters in scope (first entry per symbol)."""
    out = {}
    for e in ds.earnings:
        rep = e.get("report") or {}
        sym = e.get("symbol")
        if not sym or not rep.get("date"):
            continue
        rd = date.fromisoformat(rep["date"])
        if (rd, rep.get("timing")) in slots and sym not in out:
            out[sym] = (e, rd, rep.get("timing"))
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
    """(last close, 20-day average $ volume, 20-day average shares) or None."""
    d = _daily(ds, sym, today)
    if len(d) < 20:
        return None
    return d[-1][4], st.mean(x[4] * x[5] for x in d[-20:]), st.mean(x[5] for x in d[-20:])


def rsi14(closes):
    """Wilder RSI(14) of a close series (None if too short)."""
    if len(closes) < 15:
        return None
    gains = [max(b - a, 0) for a, b in zip(closes, closes[1:])]
    losses = [max(a - b, 0) for a, b in zip(closes, closes[1:])]
    ag, al = st.mean(gains[:14]), st.mean(losses[:14])
    for g, l in zip(gains[14:], losses[14:]):
        ag, al = (ag * 13 + g) / 14, (al * 13 + l) / 14
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def _ema(values, n):
    """EMA series (same length as values, seeded with the first value)."""
    k, out = 2 / (n + 1), [values[0]]
    for x in values[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def technicals(d):
    """Technical state from daily bars d = [(date, open, high, low, close, volume), ...] (last bar = last session).
    Every field is None when there are too few bars for it."""
    c = [x[4] for x in d]
    h = [x[2] for x in d]
    lo = [x[3] for x in d]
    v = [x[5] for x in d]
    t = {}
    if len(d) >= 35:  # MACD 12/26/9 histogram
        macd = [a - b for a, b in zip(_ema(c, 12), _ema(c, 26))]
        sig = _ema(macd, 9)
        t["macd_hist"] = macd[-1] - sig[-1]
    if len(d) >= 20:  # Bollinger 20, 2 sd
        m20 = st.mean(c[-20:])
        sd = st.pstdev(c[-20:])
        up, dn = m20 + 2 * sd, m20 - 2 * sd
        t["bb_pct"] = (c[-1] - dn) / (up - dn) if up > dn else None
        t["bb_width"] = (up - dn) / m20 * 100
        tp = [(a + b + e) / 3 for a, b, e in zip(h[-20:], lo[-20:], c[-20:])]
        vol20 = sum(v[-20:])
        t["vwap20"] = sum(x * y for x, y in zip(tp, v[-20:])) / vol20 if vol20 else None  # rolling 20-session VWAP
        t["support20"], t["resist20"] = min(lo[-20:]), max(h[-20:])
        t["rvol"] = v[-1] / st.mean(v[-21:-1]) if len(d) >= 21 and st.mean(v[-21:-1]) else None
    if len(d) >= 21:  # volume flow: on-balance volume and up-volume vs down-volume over 20 sessions
        obv = [0.0]
        for i in range(1, len(d)):
            obv.append(obv[-1] + (v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0))
        t["obv_chg"] = obv[-1] - obv[-21]
        up_v = sum(v[i] for i in range(len(d) - 20, len(d)) if c[i] > c[i - 1])
        dn_v = sum(v[i] for i in range(len(d) - 20, len(d)) if c[i] < c[i - 1])
        t["updown"] = up_v / dn_v if dn_v else None
    if len(d) >= 60:
        t["support60"], t["resist60"] = min(lo[-60:]), max(h[-60:])
    if len(d) >= 50:
        t["sma50"] = st.mean(c[-50:])
    if len(d) >= 200:
        t["sma200"] = st.mean(c[-200:])
    if len(d) >= 1:  # classic pivots from the last session
        p = (h[-1] + lo[-1] + c[-1]) / 3
        t["pivot"], t["r1"], t["s1"] = p, 2 * p - lo[-1], 2 * p - h[-1]
    return t


def screen_fail(ds, sym, today):
    """Why a reporter is excluded before the detailed calls, or None if it passes the liquidity, technical and context filters."""
    d = _daily(ds, sym, today)
    liq = liquidity(ds, sym, today)
    if not liq or len(d) < 21:
        return "no bars"
    close, dvol, shares = liq
    if close < MIN_PRICE or dvol < MIN_DVOL:
        return "liquidity"
    if shares < MIN_SHARES:
        return "share volume"
    tr = [max(d[i][2], d[i - 1][4]) - min(d[i][3], d[i - 1][4]) for i in range(1, len(d))]
    if st.mean(tr[-14:]) / close * 100 < MIN_ATR:
        return "ATR"
    rsi = rsi14([x[4] for x in d])
    if rsi is None or not RSI_BAND[0] <= rsi <= RSI_BAND[1]:
        return "RSI"
    if abs(d[-1][4] / d[-2][4] - 1) * 100 > MAX_PRIOR_MOVE:
        return "prior-day move"
    return None


def _price(q):
    """Latest price from a quote: whichever of regular / extended-hours trade is more recent."""
    quote = q.get("quote", {})
    a, b = quote.get("venue_last_trade_time") or "", quote.get("venue_last_non_reg_trade_time") or ""
    p = quote.get("last_non_reg_trade_price") if b > a else quote.get("last_trade_price")
    return _f(p), _f(quote.get("adjusted_previous_close"))


def score(ds, sym, entry, today, reacted=True):
    """Score one reporter. today = its report date; reacted = the report has already happened (so a BMO reaction exists)."""
    d = _daily(ds, sym, today)
    if len(d) < 21:
        return None
    close = d[-1][4]
    tr = [max(d[i][2], d[i - 1][4]) - min(d[i][3], d[i - 1][4]) for i in range(1, len(d))]
    atr_pct = st.mean(tr[-14:]) / close * 100
    pts, why = {}, {}
    timing = (entry.get("report") or {}).get("timing")
    est, act = _f((entry.get("eps") or {}).get("estimate")), _f((entry.get("eps") or {}).get("actual"))
    # reaction (only once the company has reported: BMO names that have already reported)
    gap = None
    q = ds.quotes.get(sym)
    if q and timing == "am" and reacted:
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
    tech = technicals(d)
    if tech.get("vwap20"):
        gap_v = (close / tech["vwap20"] - 1) * 100
        pts["VWAP"] = 1 if close > tech["vwap20"] else -1
        why["VWAP"] = f"{gap_v:+.1f}% vs 20d VWAP {tech['vwap20']:.2f}"
    if tech.get("sma200"):
        pts["SMA200"] = 1 if close > tech["sma200"] else -1
        why["SMA200"] = f"{(close / tech['sma200'] - 1) * 100:+.1f}% vs 200d avg"
    if tech.get("macd_hist") is not None:
        pts["MACD"] = 1 if tech["macd_hist"] > 0 else -1
        why["MACD"] = f"histogram {tech['macd_hist']:+.2f}"
    if tech.get("updown") is not None and tech.get("obv_chg") is not None:
        ud = tech["updown"]
        pts["volume flow"] = 1 if ud >= 1.2 and tech["obv_chg"] > 0 else -1 if ud <= 1 / 1.2 and tech["obv_chg"] < 0 else 0
        why["volume flow"] = f"up/down volume {ud:.2f}x, OBV {'up' if tech['obv_chg'] > 0 else 'down'} (20d)"
    if tech.get("bb_pct") is not None:
        why["Bollinger"] = f"%B {tech['bb_pct']:.2f}, band width {tech['bb_width']:.1f}%"
    if tech.get("rvol") is not None:
        why["RVOL"] = f"{tech['rvol']:.1f}x 20d avg volume"
    lv = []
    if tech.get("support20") is not None:
        lv.append(f"support {tech['support20']:.2f} / resistance {tech['resist20']:.2f} (20d)")
    if tech.get("support60") is not None:
        lv.append(f"{tech['support60']:.2f} / {tech['resist60']:.2f} (60d)")
    if tech.get("pivot") is not None:
        lv.append(f"pivot {tech['pivot']:.2f}, R1 {tech['r1']:.2f}, S1 {tech['s1']:.2f}")
    if lv:
        why["levels"] = "; ".join(lv)
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
    return {"sym": sym, "timing": timing, "rdate": today, "reacted": reacted, "reported": act is not None or "reaction" in pts,
            "total": total, "label": label, "pts": pts, "why": why, "atr_pct": atr_pct, "gap": gap, "surprise": surprise,
            "est": est, "act": act, "beat": beat, "up": up, "avg_move": avg_move, "price": close, "tech": tech}


def shortlist(ds, slots, n=DETAIL_N):
    """Reporters in scope that pass the screen, most traded (by $ volume) first."""
    rows = []
    for s, (_, rd, _) in candidates(ds, slots).items():
        if screen_fail(ds, s, rd) is None:
            rows.append((s, liquidity(ds, s, rd)[1]))
    return [s for s, _ in sorted(rows, key=lambda x: -x[1])[:n]]


# ---------------------------------------------------------------- calls per stage
def calls_calendar(slots):
    return [(P + "get_earnings_calendar", {"days": 1, "filter": "high_market_cap", "start_date": str(d)})
            for d in sorted({d for d, _ in slots})]


def calls_screen(ds, slots):
    syms = sorted(candidates(ds, slots)) + ["SPY"]
    start = f"{min(d for d, _ in slots) - timedelta(days=300)}T00:00:00Z"  # 200-day average + 20-day levels
    return [(P + "get_equity_historicals", {"symbols": c, "interval": "day", "start_time": start}) for c in chunks(syms, 10)]


def calls_detail(ds, slots):
    syms = shortlist(ds, slots)
    if not syms:
        return []
    calls = [(P + "get_equity_quotes", {"symbols": syms}),
             (P + "get_equity_analyst_ratings", {"symbols": syms})]
    start = f"{min(d for d, _ in slots) - timedelta(days=800)}T00:00:00Z"  # 8 quarters of report-day moves
    calls += [(P + "get_equity_historicals", {"symbols": c, "interval": "day", "start_time": start}) for c in chunks(syms, 10)]
    calls += [(P + "get_earnings_results", {"symbol": s}) for s in syms]
    return calls


# ---------------------------------------------------------------- report
def _label(r):
    return {"BULLISH": '<span class="g">Bullish</span>', "BEARISH": '<span class="r">Bearish</span>'}.get(r["label"], "Neutral")


def _when(r, day):
    if r["timing"] == "am":
        if r["reacted"]:
            return "BMO, reported"
        return "BMO today" if r["rdate"] == day else f"BMO {r['rdate']:%a %b %d}"
    return "AMC tonight" if r["rdate"] == day else f"AMC {r['rdate']:%a %b %d}"


def _rows(picks, day):
    rows = []
    for i, r in enumerate(picks, 1):
        rows.append([i, f"<b>{r['sym']}</b>", _when(r, day), _label(r), f"{r['total']:+d}",
                     R.pct(r["gap"], 1) if r["gap"] is not None else "n/a",
                     f"{r['est']:.2f}" if r["est"] is not None else "n/a",
                     f"{r['act']:.2f} ({r['surprise']:+.0f}%)" if r["surprise"] is not None else "not yet",
                     f"{r['beat']:.0%}" if r["beat"] is not None else "n/a",
                     f"&plusmn;{r['avg_move']:.1f}%" if r["avg_move"] is not None else "n/a",
                     f"{r['atr_pct']:.1f}%"])
    return rows


def build(ds, now, test=False):
    day, slots = plan(now)
    cands = candidates(ds, slots)
    short = shortlist(ds, slots)
    scored = []
    for s in short:
        e, rd, _ = cands[s]
        r = score(ds, s, e, rd, reacted=rd <= now.date())
        if r:
            scored.append(r)
    scored.sort(key=lambda r: (-abs(r["total"]), short.index(r["sym"])))
    bull = [r for r in scored if r["label"] == "BULLISH"][:TOP_N]
    bear = [r for r in scored if r["label"] == "BEARISH"][:TOP_N]
    picked = bull + bear
    title = f"{'[TEST] ' if test else ''}ER Research - {now:%Y-%m-%d %H:%M} CT"
    if now.hour < 12:
        scope = f"Morning run: {day:%a %b %d} before-the-open and after-the-close reporters"
    else:
        scope = f"Afternoon run: {day:%a %b %d} after-the-close and {slots[1][0]:%a %b %d} before-the-open reporters"
    note = (f"{scope}. {len(cands)} reporters in scope; {len(short)} pass the screen (price >= ${MIN_PRICE:.0f}, "
            f">= ${MIN_DVOL / 1e6:.0f}M/day and >= {MIN_SHARES / 1e6:.0f}M shares/day, ATR >= {MIN_ATR}%, RSI "
            f"{RSI_BAND[0]}-{RSI_BAND[1]}, prior-day move <= {MAX_PRIOR_MOVE:.0f}%). The top {TOP_N} per side come from the "
            f"{DETAIL_N} most traded.")
    head = ["#", "Stock", "Report", "Call", "Score", "Move", "EPS est", "EPS actual", "Beat rate (8q)", "Avg ER move", "ATR"]
    body = f"<h3>1. Top {TOP_N} Bullish</h3>"
    body += R.table(head, _rows(bull, day), left=3, tint=3) if bull else "<p>No Bullish setups in this run.</p>"
    body += f"<h3>2. Top {TOP_N} Bearish</h3>"
    body += R.table(head, _rows(bear, day), left=3, tint=3) if bear else "<p>No Bearish setups in this run.</p>"
    body += "<h3>3. Why</h3><ul>" + "".join(
        f"<li><b>{r['sym']}</b> {_label(r)} ({r['total']:+d}): "
        + "; ".join(f"{k} {r['pts'][k]:+d} ({escape(r['why'][k])})" for k in r["pts"]) + "</li>"
        + (f"<li style='list-style:none;margin-left:-18px;color:#4b5563'>Levels: {escape(r['why']['levels'])}; "
           f"{escape(r['why'].get('Bollinger', ''))}; {escape(r['why'].get('RVOL', ''))}</li>" if 'levels' in r['why'] else "")
        for r in picked) + "</ul>"
    rest = [r for r in scored if r not in picked]
    if rest:
        body += "<h3>4. Rest of the screened list</h3><p>" + ", ".join(f"{r['sym']} {_label(r)} {r['total']:+d}" for r in rest) + "</p>"
    body += ("<h3>Method</h3><p>Fixed-weight checklist, nothing tuned: reaction since the prior close in ATR units (BMO names that "
             "have already reported, up to &plusmn;3), EPS surprise (&plusmn;1), 8-quarter beat rate (&plusmn;1), up-day rate after "
             "past reports (&plusmn;1), 20-day return vs SPY (&plusmn;1), price vs 50-day average (&plusmn;1), analyst buy share and "
             "target (&plusmn;1), VWAP, 200-day average, MACD, volume flow (up/down volume and OBV) (&plusmn;1 each). Score &ge; +2 Bullish, &le; -2 Bearish. <b>Not validated out of sample</b>: post-earnings "
             "direction is close to a coin flip. Names reporting after the close, and next session's before-the-open names, have no "
             "reaction yet, so their call rests on history, trend and analysts. Size positions for the average earnings move shown.</p>")
    missing = [s for s in short if s not in {r["sym"] for r in scored}]
    return title, R.doc(title, note, body), missing, scored


def main(argv=None):
    ap = argparse.ArgumentParser(description="ER agent: earnings reporters, research only")
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
        _, slots = plan(now)
        calls = {"calendar": lambda: calls_calendar(slots), "screen": lambda: calls_screen(ds, slots),
                 "detail": lambda: calls_detail(ds, slots)}[a.stage]()
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
