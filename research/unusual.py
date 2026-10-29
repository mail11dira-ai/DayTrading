"""UNUSUAL agent: market-wide unusual options flow, scored like a quant desk would - research only, no orders.

Five stages, each printing the read-only Robinhood calls for the next one (the names depend on the scan):
  scan (one market-wide preview_scan) -> chains (expirations for the shortlist) -> contracts (one page of
  nearest-expiry calls and puts around the price) -> quotes (option quotes: volume, OI, bid/ask, IV, greeks) -> report (HTML email).

Scan filter (pace-adjusted to the time of day, so a 9 am run is not compared with full-day averages):
  options volume > 2 x 10-day average, options premium >= $5M, price >= $10, market cap >= $2B (ETFs have no
  market cap and drop out: index-ETF flow is mostly hedging, not a directional bet).

Score = direction (fixed weights, nothing tuned, NOT validated out of sample):
  premium mix   call share of options premium >= 70% -> +2, >= 60% -> +1, <= 30% -> -2, <= 40% -> -1
  contracts     contracts with volume > OI and premium >= $50K: call share of that premium >= 65% -> +1, <= 35% -> -1
  tape          stock change >= +1% -> +1, <= -1% -> -1 (flow confirmed by price)
Label: >= +2 Bullish, <= -2 Bearish, else Neutral. Ranked by intensity (options RVOL, stock RVOL, volume/OI, premium size)
then premium. GEX, IV rank, front/back IV and earnings date are shown as context, not scored.
Not available from Robinhood: sweeps and trade side (bid/ask aggressor) - quotes carry no prints. The email says so.
"""
import argparse
import base64
import json
import math
from datetime import date, datetime, timedelta
from html import escape

from . import collect, render as R
from .analyze import now_ct
from .er import session_day
from .plan import P, chunks

MIN_PRICE, MIN_MCAP = 10.0, 2e9
VOL_X, MIN_PREM = 2.0, 5e6      # full-day thresholds; scaled by the share of the session elapsed
CONTRACT_PREM = 50_000          # "Premium > 50K" per contract
TOP_N = 5
STRIKES = 12                    # strikes per side nearest the money (nearest expiry) that get quotes
QUOTE_CHUNK = 120              # big enough that each result is saved to a file instead of filling the context

SCAN_COLS = [("Call vol", "optionsCallDayVolume"), ("Put vol", "optionsPutDayVolume"),
             ("Opt vol 10d avg", "optionsTotalVolumeAvg10Day"), ("Total OI", "optionsTotalOpenInterest"),
             ("Call prem", 'optionsDayPremium(callput="C")'), ("Put prem", 'optionsDayPremium(callput="P")'),
             ("IV rank", "ivRank"), ("IV30", "atmIv30Day"), ("Front IV", "frontIV"), ("Back IV", "backIV"),
             ("Earnings", "fundamental.earningsYmd"), ("Mkt cap", "fundamental.marketCap"),
             ("Chg", 'changeFromCloseAllDayRatio(candlePeriod="1d")'),
             ("Stock RVOL", 'dayVolume / volumeAvg(candleCount=30, candlePeriod="1d", session="all")')]
# the scanner renames columns that match a standard one; accept both names
ALIASES = {"call_vol": ("Total call volume", "Call vol"), "put_vol": ("Total put volume", "Put vol"),
           "avg10": ("Opt vol 10d avg",), "oi": ("Total OI", "Options open interest"),
           "call_prem": ("Call prem",), "put_prem": ("Put prem",), "prem": ("Options premium",),
           "ivr": ("IV rank",), "iv": ("Implied volatility", "IV30"), "front": ("Front IV",), "back": ("Back IV",),
           "er": ("Earnings date", "Earnings"), "mcap": ("Market cap", "Mkt cap"), "chg": ("% Change", "Chg"),
           "rvol": ("Stock RVOL",), "last": ("Last",)}


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


class Flow:
    """Scan rows, chains, contracts and option quotes from the transcript (duck-types collect.Dataset.add)."""

    def __init__(self):
        self.rows = {}        # sym -> {field: float|None}
        self.expiries = {}    # sym -> [dates]
        self.contracts = {}   # instrument id -> {sym, type, strike, exp}
        self.oquotes = {}     # instrument id -> quote dict
        self.sources = 0

    def add(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            return
        data = payload["data"]
        res = data.get("result")
        if isinstance(res, dict) and isinstance(res.get("results"), list):
            self.sources += 1
            for r in res["results"]:
                cols = r.get("columns") or {}
                row = {k: next((_f(cols[n]) for n in names if n in cols), None) for k, names in ALIASES.items()}
                if r.get("ticker"):
                    self.rows[r["ticker"]] = row
        for c in data.get("chains") or []:
            if c.get("symbol") and c.get("expiration_dates"):
                self.sources += 1
                self.expiries.setdefault(c["symbol"], sorted(c["expiration_dates"]))
        for i in data.get("instruments") or []:
            if i.get("id") and i.get("chain_symbol"):
                self.contracts[i["id"]] = {"sym": i["chain_symbol"], "type": i.get("type"),
                                           "strike": _f(i.get("strike_price")), "exp": i.get("expiration_date")}
        if data.get("instruments"):
            self.sources += 1
        for r in data.get("results") or []:
            q = r.get("quote") if isinstance(r, dict) else None
            if isinstance(q, dict) and q.get("instrument_id"):
                self.oquotes[q["instrument_id"]] = q


def pace(now):
    """Share of the regular session (8:30-15:00 CT) elapsed; 1 outside it (full day of data)."""
    m = (now.hour * 60 + now.minute) - (8 * 60 + 30)
    return 1.0 if m <= 0 or m >= 390 else max(0.1, m / 390)


def _er_date(x):
    try:
        s = str(int(x))
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (TypeError, ValueError):
        return None


def underlying(sym, row, frac, today):
    """Scan-level metrics and points for one name (None if it is not a tradable single stock)."""
    last, mcap = row.get("last"), row.get("mcap")
    if not last or last < MIN_PRICE or not mcap or mcap < MIN_MCAP:
        return None
    cp, pp = row.get("call_prem") or 0, row.get("put_prem") or 0
    cv, pv = row.get("call_vol") or 0, row.get("put_vol") or 0
    if cp + pp <= 0:
        return None
    share = cp / (cp + pp)
    chg = (row.get("chg") or 0) * 100
    avg, oi = row.get("avg10"), row.get("oi")
    orvol = (cv + pv) / avg / frac if avg else None
    srvol = row["rvol"] / frac if row.get("rvol") is not None else None
    pts, why = {}, {}
    pts["premium mix"] = 2 if share >= .7 else 1 if share >= .6 else -2 if share <= .3 else -1 if share <= .4 else 0
    why["premium mix"] = f"calls {share:.0%} of ${(cp + pp) / 1e6:,.0f}M premium"
    pts["tape"] = 1 if chg >= 1 else -1 if chg <= -1 else 0
    why["tape"] = f"stock {chg:+.1f}%"
    inten = ((2 if orvol >= 5 else 1 if orvol >= 3 else 0) if orvol else 0) + (1 if srvol and srvol >= 2 else 0) \
        + (1 if oi and (cv + pv) / oi >= .25 else 0) + (1 if cp + pp >= 5e7 else 0)
    er = _er_date(row.get("er"))
    days = (er - today).days if er else None
    front, back = row.get("front"), row.get("back")
    flags = []
    if days is not None and -1 <= days <= 7:
        flags.append("earnings today" if days == 0 else "reported" if days < 0 else f"earnings in {days}d")
    if front and back and front > 1.1 * back:
        flags.append("event IV (front > back)")
    ivr = row.get("ivr")
    if ivr is not None and ivr >= .8:
        flags.append("IV rich")
    elif ivr is not None and ivr <= .2:
        flags.append("IV cheap")
    return {"sym": sym, "price": last, "chg": chg, "prem": cp + pp, "share": share, "cv": cv, "pv": pv, "oi": oi,
            "orvol": orvol, "srvol": srvol, "iv": row.get("iv"), "ivr": ivr, "er": er, "days": days,
            "flags": flags, "pts": pts, "why": why, "intensity": inten}


def _dir(u):
    return sum(u["pts"].values())


def candidates(fl, now):
    frac, today = pace(now), session_day(now)
    return [u for u in (underlying(s, r, frac, today) for s, r in fl.rows.items()) if u]


def shortlist(fl, now, n=TOP_N):
    """Top n bullish and n bearish names on scan data alone (they get the contract-level calls)."""
    us = candidates(fl, now)
    key = lambda u: (-abs(_dir(u)), -u["intensity"], -u["prem"])
    bull = sorted((u for u in us if _dir(u) >= 1), key=key)[:n]
    bear = sorted((u for u in us if _dir(u) <= -1), key=key)[:n]
    return [u["sym"] for u in bull + bear]


def expiry(fl, sym, today):
    return next((d for d in fl.expiries.get(sym, []) if d >= str(today)), None)


def cursor(strike):
    """Page cursor that starts the strike-sorted contract list just above `strike` (format seen in `next`)."""
    return base64.b64encode(f"p={strike:.4f}".encode()).decode()


def contract_stats(fl, u, today):
    """Nearest-expiry contract metrics: unusual contracts (volume > OI, premium >= $50K), GEX, walls."""
    sym, S = u["sym"], u["price"]
    exp = expiry(fl, sym, today)
    rows = []
    for iid, c in fl.contracts.items():
        q = fl.oquotes.get(iid)
        if c["sym"] != sym or c["exp"] != exp or not q or c["strike"] is None:
            continue
        vol, oi = int(q.get("volume") or 0), int(q.get("open_interest") or 0)
        mark, bid, ask = _f(q.get("mark_price")) or 0, _f(q.get("bid_price")), _f(q.get("ask_price"))
        rows.append({"type": c["type"], "strike": c["strike"], "vol": vol, "oi": oi, "mark": mark, "bid": bid, "ask": ask,
                     "bid_size": q.get("bid_size"), "ask_size": q.get("ask_size"), "prem": vol * mark * 100,
                     "iv": _f(q.get("implied_volatility")), "gamma": _f(q.get("gamma")) or 0, "delta": _f(q.get("delta"))})
    if not rows:
        return None
    unusual = sorted((r for r in rows if r["vol"] > r["oi"] and r["prem"] >= CONTRACT_PREM), key=lambda r: -r["prem"])
    ucall = sum(r["prem"] for r in unusual if r["type"] == "call")
    uput = sum(r["prem"] for r in unusual if r["type"] == "put")
    # dealer gamma exposure, $ per 1% move: dealers assumed long calls / short puts (the usual convention)
    gex = sum(r["gamma"] * r["oi"] * 100 * S * S * 0.01 * (1 if r["type"] == "call" else -1) for r in rows)
    wall = lambda t: max((r for r in rows if r["type"] == t), key=lambda r: r["oi"], default=None)
    return {"exp": exp, "n": len(rows), "unusual": unusual, "ucall": ucall, "uput": uput, "gex": gex,
            "call_wall": (wall("call") or {}).get("strike"), "put_wall": (wall("put") or {}).get("strike")}


def score(fl, u, today):
    u = dict(u, pts=dict(u["pts"]), why=dict(u["why"]))
    cs = contract_stats(fl, u, today)
    u["cs"] = cs
    if cs and cs["ucall"] + cs["uput"] > 0:
        sh = cs["ucall"] / (cs["ucall"] + cs["uput"])
        u["pts"]["contracts"] = 1 if sh >= .65 else -1 if sh <= .35 else 0
        u["why"]["contracts"] = (f"{len(cs['unusual'])} contracts vol > OI and >= $50K: "
                                 f"calls {sh:.0%} of ${(cs['ucall'] + cs['uput']) / 1e6:,.1f}M")
    u["total"] = _dir(u)
    u["label"] = "BULLISH" if u["total"] >= 2 else "BEARISH" if u["total"] <= -2 else "NEUTRAL"
    return u


# ---------------------------------------------------------------- calls per stage
def calls_scan(now):
    frac = pace(now)
    k, prem = round(max(0.3, VOL_X * frac), 2), round(max(1e6, MIN_PREM * frac))
    filters = [{"expression": f"optionsTotalDayVolume > {k} * optionsTotalVolumeAvg10Day", "predicate": "PREDICATE_EQUAL",
                "values": ["True"], "display_title": "Options vol vs 10d avg"},
               {"expression": "optionsDayPremium()", "predicate": "PREDICATE_GREATER_THAN_OR_EQUAL", "values": [str(prem)],
                "display_title": "Options premium"},
               {"expression": "tradeAllDay.price", "predicate": "PREDICATE_GREATER_THAN_OR_EQUAL", "values": [str(int(MIN_PRICE))],
                "display_title": "Price"}]
    return [(P + "preview_scan", {"filters": filters, "columns": [{"display_name": n, "expression": e} for n, e in SCAN_COLS]})]


def calls_chains(fl, now):
    return [(P + "get_option_chains", {"underlying_symbol": s}) for s in shortlist(fl, now)]


def calls_contracts(fl, now):
    today, out = session_day(now), []
    price = {u["sym"]: u["price"] for u in candidates(fl, now)}
    for s in shortlist(fl, now):
        exp = expiry(fl, s, today)
        if exp:  # one page (~100 contracts, calls and puts interleaved by strike) starting 7% below the price
            out.append((P + "get_option_instruments", {"chain_symbol": s, "expiration_dates": exp,
                                                       "cursor": cursor(price[s] * 0.93)}))
    return out


def calls_quotes(fl, now):
    today, ids = session_day(now), []
    price = {u["sym"]: u["price"] for u in candidates(fl, now)}
    for s in shortlist(fl, now):
        exp = expiry(fl, s, today)
        for t in ("call", "put"):
            cs = [(abs(c["strike"] - price[s]), iid) for iid, c in fl.contracts.items()
                  if c["sym"] == s and c["exp"] == exp and c["type"] == t and c["strike"] is not None]
            ids += [iid for _, iid in sorted(cs)[:STRIKES]]
    return [(P + "get_option_quotes", {"instrument_ids": c}) for c in chunks(ids, QUOTE_CHUNK)]


# ---------------------------------------------------------------- report
def _label(r):
    return {"BULLISH": '<span class="g">Bullish</span>', "BEARISH": '<span class="r">Bearish</span>'}.get(r["label"], "Neutral")


def _m(x):
    if x is None:
        return "n/a"
    a, sign = abs(x), "-" if x < 0 else ""
    return sign + (f"${a / 1e9:,.1f}B" if a >= 1e9 else f"${a / 1e6:,.1f}M" if a >= 1e6 else f"${a / 1e3:,.0f}K")


def _contract(c, exp):
    out = f"{c['type'][0].upper()} {c['strike']:g} {exp[5:]}: vol {c['vol']:,} vs OI {c['oi']:,}, {_m(c['prem'])}"
    out += f", IV {c['iv'] * 100:.0f}%" if c["iv"] else ""
    if c["bid"] and c["ask"]:
        spread = (c["ask"] - c["bid"]) / ((c["ask"] + c["bid"]) / 2) * 100
        out += f", bid {c['bid']:.2f}x{c['bid_size']} / ask {c['ask']:.2f}x{c['ask_size']} ({spread:.1f}% spread)"
    return out


def _rows(top):
    rows = []
    for i, r in enumerate(top, 1):
        cs = r.get("cs")
        c = cs["unusual"][0] if cs and cs["unusual"] else None
        top_c = f"{c['type'][0].upper()} {c['strike']:g} vol {c['vol']:,} / OI {c['oi']:,}" if c else "none"
        rows.append([i, f"<b>{r['sym']}</b>", _label(r), f"{r['total']:+d}", f"{r['price']:,.2f}", R.pct(r["chg"], 1),
                     f"{_m(r['prem'])} ({r['share']:.0%} C)", f"{r['orvol']:.1f}x" if r["orvol"] else "n/a",
                     f"{r['srvol']:.1f}x" if r["srvol"] else "n/a",
                     f"{len(cs['unusual'])} / {_m(cs['ucall'] + cs['uput'])}" if cs else "n/a", top_c,
                     (f"{r['iv'] * 100:.0f}%" if r["iv"] else "n/a") + (f" / {r['ivr'] * 100:.0f}" if r["ivr"] is not None else ""),
                     _m(cs["gex"]) if cs else "n/a", escape(", ".join(r["flags"])) or "-"])
    return rows


HEAD = ["#", "Stock", "Call", "Score", "Price", "Chg", "Opt premium", "Opt RVOL", "Stock RVOL", "Unusual (n / $)",
        "Top contract", "IV / rank", "GEX per 1%", "Catalyst"]


def build(fl, now, test=False):
    today = session_day(now)
    short = shortlist(fl, now)
    by = {u["sym"]: u for u in candidates(fl, now)}
    scored = [score(fl, by[s], today) for s in short]
    key = lambda r: (-r["intensity"], -r["prem"])
    bull = sorted((r for r in scored if r["label"] == "BULLISH"), key=key)[:TOP_N]
    bear = sorted((r for r in scored if r["label"] == "BEARISH"), key=key)[:TOP_N]
    title = f"{'[TEST] ' if test else ''}UNUSUAL Options Flow - {now:%Y-%m-%d %H:%M} CT"
    frac = pace(now)
    note = (f"{len(fl.rows)} names pass the scan (options volume > 2x the 10-day average and premium >= $5M, "
            f"pace-adjusted to {frac:.0%} of the session); {len(by)} are single stocks >= ${MIN_PRICE:.0f} and "
            f">= ${MIN_MCAP / 1e9:.0f}B market cap; {len(short)} get contract-level detail.")
    body = ""
    for n, (name, lst) in enumerate((("Top 5 bullish flow", bull), ("Top 5 bearish flow", bear)), 1):
        body += f"<h3>{n}. {name}</h3>"
        body += R.table(HEAD, _rows(lst), left=3, tint=3) if lst else "<p>None today.</p>"
    body += "<h3>3. Why and the contracts</h3><ul>"
    for r in bull + bear:
        cs = r.get("cs")
        body += (f"<li><b>{r['sym']}</b> {_label(r)} ({r['total']:+d}): "
                 + "; ".join(f"{k} {r['pts'][k]:+d} ({escape(r['why'][k])})" for k in r["pts"]))
        if cs:
            body += (f". Walls ({cs['exp']}): call {cs['call_wall']:g} / put {cs['put_wall']:g}, GEX {_m(cs['gex'])} per 1% "
                     f"({'dampening' if cs['gex'] > 0 else 'amplifying'})" if cs["call_wall"] and cs["put_wall"] else "")
            body += "".join(f"<br>&nbsp;&nbsp;{escape(_contract(c, cs['exp']))}" for c in cs["unusual"][:3])
        body += "</li>"
    body += "</ul>"
    rest = [r for r in scored if r not in bull and r not in bear]
    if rest:
        body += "<h3>4. Also screened</h3><p>" + ", ".join(f"{r['sym']} {_label(r)} {r['total']:+d}" for r in rest) + "</p>"
    body += ("<h3>Method</h3><p>Fixed-weight checklist, nothing tuned: call share of options premium (&plusmn;2), call share of "
             "unusual-contract premium (volume &gt; open interest and &ge; $50K, nearest expiry, &plusmn;1), stock move "
             "&ge; 1% (&plusmn;1). Score &ge; +2 Bullish, &le; -2 Bearish; ranked by options RVOL, stock RVOL, volume/OI and "
             "premium size. RVOL is pace-adjusted to the time of day. GEX uses the nearest expiry's "
             f"{STRIKES} strikes each side, assuming dealers are long calls and short puts (positive = moves dampened). "
             "<b>Not available from Robinhood: sweeps and trade side</b> (no prints, only bid/ask quotes), so premium can be "
             "sold as well as bought; a call-heavy mix can be covered-call writing. <b>Not validated out of sample.</b></p>")
    missing = [r["sym"] for r in scored if not r["cs"]]
    return title, R.doc(title, note, body), missing, scored


NOW_FILE = "/tmp/unusual_now.txt"


def _pinned_now(stage, override):
    """Every stage uses the scan's time, so the pace-adjusted shortlist cannot change between stages."""
    if override:
        return now_ct(override)
    now = now_ct(None)
    if stage == "scan":
        with open(NOW_FILE, "w") as f:
            f.write(now.isoformat())
        return now
    try:
        with open(NOW_FILE) as f:
            pinned = now_ct(f.read().strip())
        return pinned if pinned.date() == now.date() and now - pinned < timedelta(hours=2) else now
    except (OSError, ValueError):
        return now


def main(argv=None):
    ap = argparse.ArgumentParser(description="UNUSUAL agent: unusual options flow, research only")
    ap.add_argument("stage", choices=["scan", "chains", "contracts", "quotes", "report"])
    ap.add_argument("--transcript")
    ap.add_argument("--data", help="directory of raw tool-result JSON files")
    ap.add_argument("--now", help="override current time (ISO, CT if no offset)")
    ap.add_argument("--out", default="/tmp/unusual_report.html")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args(argv)
    now = _pinned_now(a.stage, a.now)
    fl = Flow()
    if a.stage != "scan":
        if a.data:
            collect.load_dir(a.data, fl)
        if a.transcript or not a.data:
            path = a.transcript or collect.latest_transcript()
            if path:
                collect.load_transcript(path, fl)
    if a.stage != "report":
        calls = {"scan": lambda: calls_scan(now), "chains": lambda: calls_chains(fl, now),
                 "contracts": lambda: calls_contracts(fl, now), "quotes": lambda: calls_quotes(fl, now)}[a.stage]()
        for tool, args in calls:
            print(json.dumps({"tool": tool, "args": args}))
        return
    from .report import _write_parts
    title, html, missing, scored = build(fl, now, a.test)
    with open(a.out, "w") as f:
        f.write(html)
    parts = _write_parts(a.out, html.replace("</li>", "</li>\n").replace("</table>", "</table>\n"), 24000)
    print(json.dumps({"subject": title, "parts": parts, "bytes": len(html), "scored": len(scored), "missing": missing}))


if __name__ == "__main__":
    main()
