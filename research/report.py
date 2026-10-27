"""Build the MAG 7 / AI Sectors HTML email from collected Robinhood data.

Usage (inside a routine session, after the Robinhood tool calls):
    python -m research.report --agent mag7 --out /tmp/report.html
    python -m research.report --agent aisectors --data DIR --now 2026-10-12T15:00 --test

Prints a one-line JSON summary (subject, output path, size, missing symbols).
"""
import argparse
import json
import sys
from html import escape

from . import collect, market as M, render as R
from .analyze import analyze, detect_mode, earnings_within, now_ct
from .universe import (AI_SECTORS, EMPTY_LAYER_NOTE, INVERSE, modern_layout, symbols)

TITLES = {"mag7": "MAG 7", "aisectors": "AI Sectors", "modern": "Modern AI Sectors", "ai100": "AI Sectors 100",
          "super100": "Super 100"}


def build(agent, ds, now, test=False):
    syms, bench = symbols(agent)
    mode, sday = detect_mode(ds, now)
    res = {s: analyze(ds, s, mode, sday, now) for s in syms + bench}
    missing = [s for s, r in res.items() if not r["ok"]]
    qqq = res.get("QQQ", {})
    q_pct = qqq.get("day_pct") if qqq.get("ok") else None
    q15, q30 = (qqq.get("ret15"), qqq.get("ret30")) if qqq.get("ok") else (None, None)
    for r in res.values():
        r["vs_qqq"] = r["day_pct"] - q_pct if (r["ok"] and q_pct is not None) else None
        r["rs15"] = r["ret15"] - q15 if (r["ok"] and r.get("ret15") is not None and q15 is not None) else None
        r["rs30"] = r["ret30"] - q30 if (r["ok"] and r.get("ret30") is not None and q30 is not None) else None
    earn = earnings_within(ds, set(syms + bench), sday if mode == "closed" else now.date())

    stamp = now.strftime("%Y-%m-%d %H:%M")
    title = f"{TITLES[agent]} Research - {stamp} CT"
    if mode == "premarket":
        note = f"Pre-market run: prices are extended-hours; intraday VWAP/RVOL/opening range not available yet. Prior session {sday}."
        title += " (pre-market)"
    elif mode == "closed":
        note = f"Market closed: all intraday figures use the {sday} regular session; price = that session's close."
        title += f" (as of {sday} close)"
    else:
        note = f"Intraday run on the {sday} session (regular hours 8:30-15:00 CT)."
    if test:
        title = "[TEST] " + title
    if missing:
        note += f" No data for: {', '.join(missing)}."

    if agent in ("modern", "ai100", "super100"):
        body = _modern(res, syms, bench, earn, ds, agent, sday)
    else:
        body = _mag7(res, syms, bench, earn, ds, sday) if agent == "mag7" else _ai(res, syms, bench, earn, ds)
    return title, R.doc(title, note, body), missing, mode


def _breadth(res, syms, ds):
    """Breadth / regime lines for the snapshot: how broad is the move, plus VIX."""
    ok = [res[s] for s in syms if res[s]["ok"] and s not in INVERSE]
    n = len(ok)
    if not n:
        return []
    cl = lambda p: "g" if p >= 60 else "r" if p <= 40 else "z"
    sp = lambda p, txt: f'<span class="{cl(p)}">{txt}</span>'
    up = 100 * sum(1 for r in ok if r["day_pct"] > 0) / n
    vw = [r for r in ok if r["vwap"] and not r["thin"]]
    ab = 100 * sum(1 for r in vw if r["price"] > r["vwap"]) / len(vw) if vw else None
    hold = 100 * sum(1 for r in ok if r.get("hold_821") == "holding") / n
    bull = sum(1 for r in ok if r["bias_label"] == "BULLISH")
    bear = sum(1 for r in ok if r["bias_label"] == "BEARISH")
    lead = sum(1 for r in ok if (r.get("rs30") or 0) >= 0.3)
    parts = [sp(up, f"{up:.0f}% up")]
    if ab is not None:
        parts.append(sp(ab, f"{ab:.0f}% above VWAP"))
    parts.append(sp(hold, f"{hold:.0f}% holding 8/21"))
    parts.append(f'<span class="g">{bull} bullish</span> / <span class="r">{bear} bearish</span> bias')
    parts.append(f"{lead} leading QQQ (30m)")
    # Regime uses today's (intraday) measures only; holding 8/21 is slow daily context and
    # was not predictive in backtests/bias_validation.md, so it is shown but not scored.
    score = [up] + ([ab] if ab is not None else [])
    avg = sum(score) / len(score)
    regime = R.pill("RISK-ON" if avg >= 60 else "RISK-OFF" if avg <= 40 else "MIXED", cl(avg))
    out = [f"<li><b>Breadth ({n} stocks):</b> " + " &middot; ".join(parts) + f" &rarr; {regime}</li>"]
    vix = (getattr(ds, "indexes", {}) or {}).get("VIX")
    if vix is not None:
        lab = "calm" if vix < 15 else "normal" if vix < 20 else "elevated" if vix < 30 else "high"
        c = "g" if vix < 20 else "r" if vix >= 25 else "z"
        out.append(f'<li><b>VIX</b> <span class="{c}">{vix:.1f}</span> ({lab})</li>')
    return out


def _snapshot(res, bench, extra_line, more=()):
    items = []
    for b in bench:
        r = res[b]
        if not r["ok"]:
            items.append(f"<li><b>{b}</b> {R.NA}</li>")
            continue
        vw = f"VWAP {R.num(r['vwap'])} (px {R.pct(r['vs_vwap'])})" if r["vwap"] else f"VWAP {R.NA}"
        items.append(f"<li><b>{b}</b> {R.num(r['price'])} ({R.pct(r['day_pct'])}); {vw}; "
                     f"bias {R.bias(r)}; RVOL {R.ratio(r['rvol'])}</li>")
    items.append(f"<li>{extra_line}</li>")
    items += list(more)
    return "<h3>1. Market snapshot</h3><ul>" + "".join(items) + "</ul>"


def _row(r, first=None):
    lead = [first] if first is not None else []
    if not r["ok"]:
        return lead + [f"<b>{r['sym']}</b>"] + [R.NA] * 13
    return lead + [f"<b>{r['sym']}</b>", R.num(r["price"]), R.pct(r["day_pct"]), R.pct(r["vs_qqq"]),
                   R.pct(r.get("rs30")), R.bias(r), R.vw_cell(r), R.rvol_cell(r), f"{R.rsi(r['rsi_5'])} / {R.rsi(r['rsi_d'])}",
                   R.ratio(r["atr_pct"]) + ("%" if r["atr_pct"] else ""), R.ratio(r["range_used"]),
                   f"{R.short_lvl(r['sup'])} / {R.short_lvl(r['res'])}", R.tone(r["stack"]), f"{r.get('in_play', 0)}/4"]


HDR = ["Ticker", "Price", "Day %", "vs QQQ", "RS 30m", "Bias", "vs VWAP", "RVOL", "RSI 5m/D", "ATR%",
       "Range used", "Nearest S / R", "MA stack", "In play"]


def _top(res, syms, n):
    cands = [res[s] for s in syms if res[s]["ok"] and res[s]["bias_label"] != "NEUTRAL" and res[s]["setup"]]
    good = [r for r in cands if r["setup"]["rr"] is not None and r["setup"]["rr"] >= 1.0]
    good.sort(key=lambda r: (-r.get("in_play", 0), -abs(r["bias"]), -r.get("conf", 0), -(r["rvol"] or 0), -(r["setup"]["rr"] or 0)))
    note = ""
    if len(good) < n:
        note = (f"Only {len(good)} setup(s) qualify (BULLISH/BEARISH bias with bias-side R/R &ge; 1.0); "
                f"{len(cands) - len(good)} excluded for R/R &lt; 1.0.")
    return good[:n], note


def _ratings_extra(ds, r):
    s = r["sym"]
    out = ""
    f = ds.fundamentals.get(s)
    if f and f.get("pe_ratio"):
        out += f"; P/E {float(f['pe_ratio']):.1f}"
    a = ds.ratings.get(s)
    if a:
        pt = a.get("mean_price_target")
        out += (f"; analysts {a.get('num_buy_ratings', 0)}B/{a.get('num_hold_ratings', 0)}H/"
                f"{a.get('num_sell_ratings', 0)}S" + (f", avg PT {float(pt):,.0f}" if pt else ""))
    return out


def _risks(res, syms, earn, gap_thr, rng_thr, rsi_hi, rsi_lo):
    items = []
    e = [f"{s} {d:%m/%d} {t}".strip() for s, (d, t) in sorted(earn.items(), key=lambda x: x[1][0]) if s in syms]
    items.append("Earnings within 14 days: " + (", ".join(e[:14]) + (f" (+{len(e) - 14} more)" if len(e) > 14 else "") if e else "none in universe"))
    ok = [res[s] for s in syms if res[s]["ok"]]
    def lst(rs, f, k=12):
        more = f" (+{len(rs) - k} more)" if len(rs) > k else ""
        return ", ".join(f(r) for r in rs[:k]) + more if rs else "none"
    ip = sorted([r for r in ok if r.get("in_play", 0) >= 2], key=lambda r: (-r["in_play"], -(r["rvol"] or 0)))
    items.append("<b>Most in play</b> (2+ of: RVOL &ge; 1.5, gap &ge; 0.5 ATR, range used &ge; 1 ATR, ORB confirmed - "
                 "expect bigger moves, direction not implied): " + lst(ip, lambda r: f"{r['sym']} {r['in_play']}/4", 15))
    items.append("RVOL &gt; 2: " + lst([r for r in ok if (r["rvol"] or 0) > 2 and not r["thin"]], lambda r: f"{r['sym']} {r['rvol']:.1f}"))
    items.append(f"Gaps &gt; {gap_thr:g}%: " + lst(sorted([r for r in ok if r["gap_pct"] is not None and abs(r["gap_pct"]) > gap_thr], key=lambda r: -abs(r["gap_pct"])), lambda r: f"{r['sym']} {r['gap_pct']:+.1f}%"))
    ext = [r for r in ok if any(x is not None and (x > rsi_hi or x < rsi_lo) for x in (r["rsi_5"], r["rsi_d"]))]
    items.append(f"RSI &gt; {rsi_hi} or &lt; {rsi_lo}: " + lst(ext, lambda r: f"{r['sym']} ({R.rsi(r['rsi_5'])}/{R.rsi(r['rsi_d'])})"))
    def orb(state, d=None):
        return [r for r in ok if r.get("orb") and r["orb"]["state"] == state and (d is None or r["orb"]["dir"] == d)]
    f_orb = lambda r: f"{r['sym']} ({r['orb']['volx']:.1f}x @ {r['orb']['time']})" if r["orb"]["volx"] else f"{r['sym']} @ {r['orb']['time']}"
    items.append('ORB confirmed (15m range, breakout on volume): <span class="g">up</span> ' + lst(orb("confirmed", "up"), f_orb)
                 + ' &middot; <span class="r">down</span> ' + lst(orb("confirmed", "down"), f_orb))
    items.append("ORB failed (breakout reversed back inside): " + lst(orb("failed"), lambda r: f"{r['sym']} ({r['orb']['dir']})"))
    gq = lambda kind: [r for r in ok if r.get("gap_q") and r["gap_q"][0] == kind]
    items.append("Gap-and-go (gap + 2x pre-market volume, holding): " + lst(gq("go"), lambda r: f"{r['sym']} {R.pct(r['gap_pct'], 1)}")
                 + " &middot; fade risk (large gap, no volume edge): " + lst(gq("fade"), lambda r: f"{r['sym']} {R.pct(r['gap_pct'], 1)}"))
    items.append("Pre-market volume &gt; 2x normal: " + lst(sorted([r for r in ok if (r.get("pm_rvol") or 0) > 2], key=lambda r: -r["pm_rvol"])[:10],
                                                           lambda r: f"{r['sym']} {r['pm_rvol']:.1f}x"))
    rs = sorted([r for r in ok if r.get("rs30") is not None], key=lambda r: -r["rs30"])
    lead_rs = [r for r in rs if r["rs30"] > 0][:5]
    lag_rs = [r for r in rs[::-1] if r["rs30"] < 0][:5]
    items.append("Intraday RS leaders (30m vs QQQ): " + lst(lead_rs, lambda r: f"{r['sym']} {R.pct(r['rs30'])}")
                 + " &middot; laggards: " + lst(lag_rs, lambda r: f"{r['sym']} {R.pct(r['rs30'])}"))
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _vix_lines(v):
    """VIX and implied-move bullets for the market deep dive."""
    if not v:
        return ["<li><b>VIX:</b> n/a (no VIX data)</li>"]
    f = lambda x, d=2: R.NA if x is None else f"{x:.{d}f}"
    s = lambda x, d=2, u="": R.NA if x is None else f"{x:+.{d}f}{u}"
    side = (f"{abs(v['vs_sma20']):.0f}% {'above' if v['vs_sma20'] > 0 else 'below'} its 20-day average {f(v['sma20'])}"
            if v["vs_sma20"] is not None else "20-day average n/a")
    out = [f"<li><b>VIX {f(v['level'])}</b> ({v['regime']}; {s(v['chg'])} pts / {s(v['chg_pct'], 1, '%')} vs prior close "
           f"{f(v['prev'])}); {side}; 20-day range {f(v['lo20'])}&ndash;{f(v['hi20'])}"
           + (f"; higher than {v['pctile']:.0f}% of the last year's closes" if v["pctile"] is not None else "") + "</li>"]
    if v["open"] is not None:
        out.append(f"<li><b>VIX today:</b> open {f(v['open'])}, high {f(v['hi'])}, low {f(v['lo'])}, last 30 min {s(v['chg30'])} pts "
                   + ("(rising = traders buying protection)" if (v["chg30"] or 0) > 0.2 else
                      "(falling = fear easing)" if (v["chg30"] or 0) < -0.2 else "(flat)") + "</li>")
    if v.get("diverge"):
        out.append("<li><b>Warning:</b> " + ("SPY up while the VIX rises - the rally is being hedged; rallies like this "
                                             "often stall" if v["diverge"] == "up" else
                                             "SPY down while the VIX falls - selling without fear; often orderly, "
                                             "less likely to cascade") + "</li>")
    for key, name in (("spy", "SPY"), ("qqq", "QQQ")):
        m = v.get(key)
        if not m:
            continue
        rare = f" - SPY closed outside it on only {100 - v['band'][0]:.0f}% of recent days: trend-day risk" if v.get("band") else " - trend-day risk"
        where = {1: "price is ABOVE the band" + rare, -1: "price is BELOW the band" + rare, 0: "price is inside the band"}[m["outside"]]
        out.append(f"<li><b>{name} implied move today</b>{' (est. from VIX x QQQ/SPY ATR)' if key == 'qqq' else ''}: "
                   f"&plusmn;{m['em']:.2f}% (&plusmn;{m['pts']:.2f}) &rarr; band {f(m['lo'])}&ndash;{f(m['hi'])}; "
                   + (f"today's range has used {m['used']:.0%} of the full band; " if m["used"] is not None else "")
                   + where + "</li>")
    if v.get("band"):
        hit, ratio, n = v["band"]
        out.append(f"<li><b>How reliable is the band:</b> over the last {n} sessions SPY closed inside the prior day's VIX "
                   f"1-sigma band on {hit:.0f}% of days (theory: about 68%); the average day used {ratio:.0%} of the implied move.</li>")
    return out


def _market(res, syms, bench, ds, sday, tape):
    """Section 1 for MAG 7: SPY / QQQ / VIX deep dive for day trading."""
    spy, qqq = res.get("SPY", {}), res.get("QQQ", {})
    v = M.vix_analysis(ds, sday, spy, qqq)
    items = []
    if spy.get("ok") and qqq.get("ok"):
        d = qqq["day_pct"] - spy["day_pct"]
        r30 = (qqq["ret30"] - spy["ret30"]) if (qqq.get("ret30") is not None and spy.get("ret30") is not None) else None
        lead = "tech leading the market" if d > 0.15 else "tech lagging the market" if d < -0.15 else "moving together"
        items.append(f"<li><b>QQQ vs SPY:</b> {R.pct(d)} today" + (f", {R.pct(r30)} over the last 30 min" if r30 is not None else "")
                     + f" &rarr; {lead}</li>")
    items.append(f"<li>{tape}</li>")
    items += _breadth(res, syms, ds)[:1]  # breadth only; the VIX gets its own lines below
    items += _vix_lines(v)
    out = "<h3>1. Market deep dive (SPY, QQQ, VIX)</h3><ul>" + "".join(items) + "</ul>"
    out += R.table(HDR, [_row(res[b]) for b in bench])
    out += "".join(R.card(res[b], full_levels=True) for b in bench if res[b]["ok"])
    return out


def _mag7(res, syms, bench, earn, ds, sday=None):
    ok = [res[s] for s in syms if res[s]["ok"]]
    ups = sum(1 for r in ok if r["day_pct"] > 0)
    tape = "n/a"
    if ok:
        best = max(ok, key=lambda r: r["day_pct"])
        worst = min(ok, key=lambda r: r["day_pct"])
        avg_q = [r["vs_qqq"] for r in ok if r["vs_qqq"] is not None]
        tape = (f"Tape: {ups}/{len(ok)} MAG 7 up; avg vs QQQ {R.pct(sum(avg_q) / len(avg_q) if avg_q else None)}; "
                f"strongest {best['sym']} {R.pct(best['day_pct'])}, weakest {worst['sym']} {R.pct(worst['day_pct'])}.")
    out = _market(res, syms, bench, ds, sday, tape)
    order = sorted(syms, key=lambda s: -(res[s]["bias"] if res[s]["ok"] else -99))
    out += "<h3>2. Scoreboard</h3>" + R.table(HDR, [_row(res[s]) for s in order])
    out += "<h3>3. Technical cards</h3>" + "".join(R.card(res[s], _ratings_extra(ds, res[s])) for s in order if res[s]["ok"])
    top, note = _top(res, syms, 3)
    out += "<h3>4. Top 3 setups</h3>" + _top_html(top, note)
    out += "<h3>5. Risks / catalysts</h3>" + _risks(res, syms, earn, 2, 1.0, 70, 30)
    return out


VALIDATION_NOTE = ("Note: setups are ranked by the in-play (movement) score first, then bias. In a 65-session test on the "
                   "AI Sectors 100 stocks (Jul-Oct 2026, 8:59 CT) the in-play score predicted bigger moves, but neither it nor "
                   "the bias score predicted direction - use bias to describe the chart, not to forecast.")


def _top_html(top, note):
    items = []
    for r in top:
        s = r["setup"]
        side = R.tone("bull above" if r["bias"] > 0 else "bear below")
        items.append(f"<li><b>{r['sym']}</b> {R.bias(r)}, in play {r.get('in_play', 0)}/4, RVOL {R.rvol_cell(r)}; {side} {R.num(s['trigger'])} "
                     f"&rarr; {R.num(s['target'])}, invalid {R.num(s['stop'])}; reward {s['reward_atr']:.2f} ATR vs "
                     f"risk {s['risk_atr']:.2f} ATR (R/R {s['rr']:.2f}); confirmations {r.get('conf', 0)}/2; "
                     f"VWAP {R.vw_cell(r)}</li>")
    return ((f"<ol>{''.join(items)}</ol>" if items else "") + (f"<p>{note}</p>" if note else "")
            + f'<p class="lg">{VALIDATION_NOTE}</p>')


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _ai(res, syms, bench, earn, ds):
    eco_avgs, sections = [], []
    for eco, layers in AI_SECTORS:
        score_rows, tick_rows, lay_stats = [], [], []
        for code, name, tickers in layers:
            if not tickers:
                score_rows.append(f'<tr><td class="l">{code}</td><td class="l">{name}</td>'
                                  f'<td class="l" colspan="5">{EMPTY_LAYER_NOTE}</td></tr>')
                continue
            live = [res[s] for _, s in tickers if s and res[s]["ok"]]
            a = _avg([r["day_pct"] for r in live])
            vq = _avg([r["vs_qqq"] for r in live])
            ab = _avg([r["bias"] for r in live])
            best = max(live, key=lambda r: r["day_pct"]) if live else None
            worst = min(live, key=lambda r: r["day_pct"]) if live else None
            lay_stats.append((code, name, a, vq))
            score_rows.append([code, name, R.pct(a), R.pct(vq), R.score(ab),
                               f"{best['sym']} {R.pct(best['day_pct'])}" if best else R.NA,
                               f"{worst['sym']} {R.pct(worst['day_pct'])}" if worst else R.NA])
            for disp, s in tickers:
                if not s:
                    tick_rows.append(f'<tr><td class="l">{code}</td><td class="l"><b>{escape(disp)}</b></td>'
                                     f'<td class="l" colspan="12">n/a - not on Robinhood</td></tr>')
                else:
                    tick_rows.append(_row(res[s], code))
        eco_avg = _avg([x[2] for x in lay_stats])
        eco_avgs.append((eco, eco_avg))
        flow = _flow(lay_stats)
        sections.append((eco, eco_avg, score_rows, tick_rows, flow))

    valid = [e for e in eco_avgs if e[1] is not None]
    lead = max(valid, key=lambda e: e[1]) if valid else None
    lag = min(valid, key=lambda e: e[1]) if valid else None
    tape = "Tape: " + (f"leader {lead[0]} {R.pct(lead[1])}, laggard {lag[0]} {R.pct(lag[1])}." if lead else R.NA)
    out = _snapshot(res, bench, tape)
    for i, (eco, eco_avg, score_rows, tick_rows, flow) in enumerate(sections, 2):
        out += f"<h3>{i}. {eco} ecosystem (avg {R.pct(eco_avg)})</h3>"
        out += R.table(["Layer", "Sector", "Avg Day %", "vs QQQ", "Avg bias", "Best", "Worst"], score_rows, left=2)
        out += R.table(["Layer"] + HDR, tick_rows, left=2)
        out += f"<p><b>Money flow:</b> {flow}</p>"
    n = len(sections) + 2
    top, note = _top(res, syms, 5)
    out += f"<h3>{n}. Top 5 setups</h3>" + _top_html(top, note) + "".join(R.card(r, _ratings_extra(ds, r)) for r in top)
    out += f"<h3>{n + 1}. Risks / catalysts</h3>" + _risks(res, syms, earn, 3, 1.2, 75, 25)
    return out


def _flow(stats):
    s = [x for x in stats if x[2] is not None]
    if not s:
        return R.NA
    best = max(s, key=lambda x: x[2])
    worst = min(s, key=lambda x: x[2])
    beat = sum(1 for x in s if x[3] is not None and x[3] > 0)
    up = _avg([x[2] for x in s if x[0] in ("L1", "L2")])
    dn = _avg([x[2] for x in s if x[0] in ("L4", "L5")])
    return (f"strongest {best[0]} {best[1]} {R.pct(best[2])}, weakest {worst[0]} {worst[1]} {R.pct(worst[2])}; "
            f"{beat}/{len(s)} layers beat QQQ; upstream L1-L2 {R.pct(up)} vs downstream L4-L5 {R.pct(dn)}.")


M_HDR = ["Type", "Ticker", "Price", "Day %", "vs QQQ", "RS 30m", "20d RS", "Bias", "vs VWAP", "RVOL", "RSI 5m/D",
         "8/21", "Nearest S / R", "In play"]


def _rs(r, spy20):
    return r["ret20"] - spy20 if (r.get("ok") and r.get("ret20") is not None and spy20 is not None) else None


def _m_row(r, kind, spy20, show_type=True):
    lead = [kind] if show_type else []
    if not r["ok"]:
        return lead + [f"<b>{r['sym']}</b>"] + [R.NA] * 12
    return lead + [f"<b>{r['sym']}</b>", R.num(r["price"]), R.pct(r["day_pct"]), R.pct(r["vs_qqq"]),
            R.pct(r.get("rs30")), R.pct(_rs(r, spy20), 1), R.bias(r), R.vw_cell(r), R.rvol_cell(r),
            f"{R.rsi(r['rsi_5'])} / {R.rsi(r['rsi_d'])}", R.tone(r.get("hold_821")),
            f"{R.short_lvl(r['sup'])} / {R.short_lvl(r['res'])}", f"{r.get('in_play', 0)}/4"]


def _modern(res, syms, bench, earn, ds, agent="modern", sday=None):
    spy = res.get("SPY", {})
    qqq = res.get("QQQ", {})
    spy20 = spy.get("ret20") if spy.get("ok") else None
    qqq20 = qqq.get("ret20") if qqq.get("ok") else None
    secs = modern_layout(agent)
    has_etf = any(k == "ETF" for sec in secs for _, k, _ in sec["members"])
    score_rows, stats = [], []
    for sec in secs:
        mem = [(s, k) for s, k, _ in sec["members"] if k != "n/a" and s not in INVERSE]
        live = [res[s] for s, k in mem if res[s]["ok"]]
        etf = _avg([res[s]["day_pct"] for s, k in mem if k == "ETF" and res[s]["ok"]])
        stk = _avg([res[s]["day_pct"] for s, k in mem if k == "Stock" and res[s]["ok"]])
        a = _avg([r["day_pct"] for r in live])
        vq = _avg([r["vs_qqq"] for r in live])
        rs = _avg([_rs(r, spy20) for r in live])
        rs30 = _avg([r.get("rs30") for r in live])
        ab = _avg([r["bias"] for r in live])
        hold = [r for r in live if r.get("hold_821") == "holding"]
        best = max(live, key=lambda r: r["day_pct"]) if live else None
        worst = min(live, key=lambda r: r["day_pct"]) if live else None
        stats.append((sec, a, rs))
        score_rows.append([sec["num"], escape(sec["name"])] + ([R.pct(etf)] if has_etf else []) + [R.pct(stk), R.pct(vq), R.pct(rs30), R.pct(rs, 1),
                           R.score(ab), f"{len(hold)}/{len(live)}",
                           f"{best['sym']} {R.pct(best['day_pct'])}" if best else R.NA,
                           f"{worst['sym']} {R.pct(worst['day_pct'])}" if worst else R.NA])
    valid = [x for x in stats if x[1] is not None]
    lead = max(valid, key=lambda x: x[1]) if valid else None
    lag = min(valid, key=lambda x: x[1]) if valid else None
    tape = "Tape: " + (f"leader {lead[0]['num']} {escape(lead[0]['name'])} {R.pct(lead[1])}, "
                       f"laggard {lag[0]['num']} {escape(lag[0]['name'])} {R.pct(lag[1])}." if lead else R.NA)
    if agent == "super100":  # replaces the MAG 7 agent, so it keeps the SPY / QQQ / VIX deep dive
        out = _market(res, syms, bench, ds, sday, tape)
    else:
        out = _snapshot(res, bench, tape, _breadth(res, syms, ds))
    out += "<h3>2. Sector scoreboard</h3>" + R.table(
        ["#", "Sector"] + (["ETFs Day %", "Leaders Day %"] if has_etf else ["Avg Day %"])
        + ["vs QQQ", "RS 30m", "20d RS vs SPY", "Avg bias", "Holding 8/21", "Best", "Worst"], score_rows, left=2,
        tint=3 if has_etf else 2)  # leaders' / average day % column
    large = agent == "super100"  # large caps: MAG 7 thresholds (2% gaps, RSI 70/30); short email (no checklist, 3 setups)
    n = 3
    if not large:
        out += "<h3>3. Weekend checklist</h3>" + _checklist(res, syms, stats, spy20, qqq20)
        n = 4
    compact = agent in ("ai100", "super100")  # short email: no per-sector tables (scoreboard already has best/worst per sector)
    for sec in ([] if compact else secs):
        rows = []
        for s, k, desc in sec["members"]:
            if k == "n/a":
                rows.append(f'<tr><td class="l">ETF</td><td class="l"><b>{s}</b></td>'
                            f'<td class="l" colspan="11">n/a - not on Robinhood ({escape(desc)})</td></tr>')
            else:
                rows.append(_m_row(res[s], k, spy20, has_etf))
        out += f"<h3>{n}. {sec['num']} {escape(sec['name'])}</h3><p><i>{escape(sec['sub'])}</i></p>"
        out += R.table(M_HDR if has_etf else M_HDR[1:], rows, left=2 if has_etf else 1)
        if sec["notes"]:
            out += "<p><i>" + "; ".join(escape(x) for x in sec["notes"]) + ".</i></p>"
        n += 1
    top, note = _top(res, syms, 3 if large else 5)
    out += (f"<h3>{n}. Top {len(top)} setups</h3>" + _top_html(top, note)
            + "".join(R.card(r, _ratings_extra(ds, r), brief=large) for r in top))
    out += f"<h3>{n + 1}. Risks / catalysts</h3>" + (_risks(res, syms, earn, 2, 1.0, 70, 30) if large
                                                     else _risks(res, syms, earn, 3, 1.2, 75, 25))
    return out


def _checklist(res, syms, stats, spy20, qqq20, k=10):
    ok = [res[s] for s in syms if res[s]["ok"] and s not in INVERSE]

    def names(rs, f=lambda r: r["sym"]):
        return ", ".join(f(r) for r in rs[:k]) + (f" (+{len(rs) - k} more)" if len(rs) > k else "") if rs else "none"
    hi52 = [r for r in ok if r.get("new_high") == "52w"]
    hi20 = [r for r in ok if r.get("new_high") == "20d"]
    hold = [r for r in ok if r.get("hold_821") == "holding"]
    lost = [r for r in ok if r.get("hold_821") == "lost"]
    bar = max(x for x in (spy20, qqq20) if x is not None) if (spy20 is not None or qqq20 is not None) else None
    outp = sorted([r for r in ok if bar is not None and r.get("ret20") is not None and r["ret20"] > bar],
                  key=lambda r: -r["ret20"])
    secs = sorted([x for x in stats if x[2] is not None], key=lambda x: -x[2])
    brk = sorted([r for r in ok if r.get("breakout")], key=lambda r: -(r.get("vol_exp") or 0))
    vexp = sorted([r for r in ok if (r.get("vol_exp") or 0) >= 1.3 or (r.get("rvol") or 0) >= 1.5],
                  key=lambda r: -max(r.get("vol_exp") or 0, r.get("rvol") or 0))
    items = [
        f"<b>1. Making new highs:</b> 52-week: {names(hi52)}; 20-day: {names(hi20)}",
        f"<b>2. Holding the 8/21 trend</b> (price &gt; daily EMA8 &gt; EMA21): {len(hold)}/{len(ok)} "
        f"&mdash; <span class=\"g\">holding</span> {names(hold)}; <span class=\"r\">lost EMA21</span> {names(lost)}",
        f"<b>3. Outperforming SPY / QQQ</b> (20-day return; SPY {R.pct(spy20, 1)}, QQQ {R.pct(qqq20, 1)}): "
        + names(outp, lambda r: f"{r['sym']} {R.pct(r['ret20'], 1)}"),
        "<b>4. Relative strength by sector</b> (avg 20-day return vs SPY): strongest "
        + (", ".join(f"{x[0]['num']} {escape(x[0]['name'])} {R.pct(x[2], 1)}" for x in secs[:3]) or "n/a")
        + "; weakest " + (", ".join(f"{x[0]['num']} {escape(x[0]['name'])} {R.pct(x[2], 1)}" for x in secs[-3:][::-1]) or "n/a"),
        "<b>5. Breaking out of a base</b> (20-day range &le; 5 ATR, price above its high): " + names(brk),
        "<b>6. Volume expanding</b> (5-day avg vol &ge; 1.3x 50-day, or RVOL &ge; 1.5): "
        + names(vexp, lambda r: f"{r['sym']} {max(r.get('vol_exp') or 0, r.get('rvol') or 0):.1f}x"),
    ]
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _write_parts(out, html, limit):
    """Split html on line boundaries into <=limit-char files so each can be `cat`-ed whole."""
    chunks, cur = [], ""
    for line in html.splitlines(keepends=True):
        if cur and len(cur) + len(line) > limit:
            chunks.append(cur)
            cur = ""
        cur += line
    chunks.append(cur)
    base = out[:-5] if out.endswith(".html") else out
    paths = []
    for i, c in enumerate(chunks, 1):
        path = f"{base}.part{i}.html"
        with open(path, "w") as f:
            f.write(c)
        paths.append(path)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent", required=True, choices=["mag7", "aisectors", "modern", "ai100", "super100"])
    ap.add_argument("--transcript", help="session transcript (.jsonl); default: newest")
    ap.add_argument("--data", help="directory of raw tool-result JSON files (instead of / in addition to transcript)")
    ap.add_argument("--now", help="override current time (ISO, CT if no offset)")
    ap.add_argument("--out", default="/tmp/report.html")
    ap.add_argument("--test", action="store_true", help="prefix subject with [TEST]")
    ap.add_argument("--part-chars", type=int, default=24000,
                    help="split the HTML into files of at most this many characters (on line breaks)")
    a = ap.parse_args(argv)
    ds = collect.Dataset()
    if a.data:
        collect.load_dir(a.data, ds)
    if a.transcript or not a.data:
        path = a.transcript or collect.latest_transcript()
        if path:
            collect.load_transcript(path, ds)
    title, html, missing, mode = build(a.agent, ds, now_ct(a.now), a.test)
    html = html.replace("</h3>", "</h3>\n").replace("</li>", "</li>\n").replace("</table>", "</table>\n")
    with open(a.out, "w") as f:
        f.write(html)
    parts = _write_parts(a.out, html, a.part_chars)
    print(json.dumps({"subject": title, "out": a.out, "parts": parts, "bytes": len(html), "mode": mode,
                      "missing": missing, "results_loaded": ds.sources}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
