"""Compact HTML email rendering (MAG 7 look: bordered tables, green/red, cards).

Styles live in one <style> block with short class names to keep the HTML small,
because the agent has to pass the whole body to Gmail.
"""
import re
from html import escape

STYLE = ("<style>body{font-family:Arial,sans-serif;font-size:13px;color:#222}"
         "table{border-collapse:collapse;font-size:12px;margin:4px 0 8px}"
         "td,th{border:1px solid #bbb;padding:3px 5px;text-align:right;white-space:nowrap}"
         "th{background:#f2f2f2}td.l,th.l{text-align:left}"
         ".g{color:#0a7d2c}.r{color:#c0392b}.z{color:#555}.c{font-size:13px;margin:0 0 10px}"
         "h4{margin:10px 0 2px}</style>")
NA = "n/a"
SPAN_TD = re.compile(r'<td><span class="(\w)">([^<]*)</span></td>')


def num(x, d=2):
    return NA if x is None else f"{x:,.{d}f}"


def cls(x, pos="g", neg="r"):
    if x is None:
        return ""
    return pos if x > 0 else neg if x < 0 else "z"


def pct(x, d=2, unit="%"):
    if x is None:
        return NA
    return f'<span class="{cls(x)}">{x:+.{d}f}{unit}</span>'


def bias(r):
    c = {"BULLISH": "g", "BEARISH": "r"}.get(r["bias_label"], "z")
    return f'<span class="{c}">{r["bias"]:+d} {r["bias_label"]}</span>'


def rsi(x):
    if x is None:
        return NA
    c = "r" if x > 70 else "g" if x < 30 else ""
    return f'<span class="{c}">{x:.0f}</span>' if c else f"{x:.0f}"


def ratio(x, d=2):
    return NA if x is None else f"{x:.{d}f}"


def lvl(z, price, atr):
    if not z:
        return NA
    p, lab = z
    dist = (p / price - 1) * 100
    s = f"{escape(lab)} {num(p)}"
    if atr:
        s += f" ({dist:+.1f}%, {abs(p - price) / atr:.2f} ATR)"
    return s


def short_lvl(z):
    return NA if not z else f"{num(z[0])}"


def table(headers, rows, left=1):
    h = "".join(f'<th class="l">{x}</th>' if i < left else f"<th>{x}</th>" for i, x in enumerate(headers))
    body = []
    for row in rows:
        if isinstance(row, str):
            body.append(row)
            continue
        body.append("<tr>" + "".join(
            f'<td class="l">{x}</td>' if i < left else f"<td>{x}</td>" for i, x in enumerate(row)) + "</tr>\n")
    out = f'<table border="1"><tr>{h}</tr>{"".join(body)}</table>'
    return SPAN_TD.sub(r'<td class="\1">\2</td>', out)


def vw_cell(r):
    if r["thin"]:
        return "thin"
    return pct(r["vs_vwap"])


def rvol_cell(r):
    return "thin" if r["thin"] else ratio(r["rvol"])


def setup_line(side, s, word):
    if not s:
        return f"{word}: {NA}"
    poor = " (poor)" if s["rr"] is not None and s["rr"] < 1 else ""
    return (f"{word} {num(s['trigger'])} ({escape(s['trigger_label'])}) &rarr; "
            f"{num(s['target'])} ({escape(s['target_label'])}) [{s['reward_atr']:.2f} ATR]; "
            f"invalid {num(s['stop'])} ({escape(s['stop_label'])}) [{s['risk_atr']:.2f} ATR]; "
            f"R/R {ratio(s['rr'])}{poor}")


def card(r, extra=""):
    p, atr, lv = r["price"], r["atr"], r["levels"]
    g = lambda k: num(lv.get(k))
    spikes = ", ".join(f"{t} {m:.1f}x {d}" for t, m, d in r["spikes"][:4]) or "none"
    trend = NA if r["vol_trend"] is None else f"{r['vol_trend']:.1f}x session avg ({'rising' if r['vol_trend'] >= 1 else 'falling'})"
    if r["vwap"] and not r["thin"]:
        sd = r["vwap_sd"] or 0
        ev = f"{r['vwap_event'][0]} VWAP @ {r['vwap_event'][1]} CT" if r["vwap_event"] else "no reclaim/loss"
        vw = (f"{num(r['vwap'])}, px {pct(r['vs_vwap'])} / {ratio(r['vs_vwap_atr'])} ATR; "
              f"&plusmn;1&sigma; {num(r['vwap'] - sd)}&ndash;{num(r['vwap'] + sd)}, "
              f"&plusmn;2&sigma; {num(r['vwap'] - 2 * sd)}&ndash;{num(r['vwap'] + 2 * sd)}; "
              f"slope {r['vwap_slope'] or NA}; {ev}")
    else:
        vw = "thin (OTC / low volume)" if r["thin"] else NA
    gap = NA if r["gap_pct"] is None else (
        f"{r['gap_pct']:+.2f}%" + ("" if r["gap_filled"] is None else f" (filled: {'yes' if r['gap_filled'] else 'no'})"))
    ema5 = NA
    if r["ema_bull"] is not None:
        ema5 = (f"EMA9 {num(r['ema9_5'])} {'&gt;' if r['ema_bull'] else '&lt;'} EMA21 {num(r['ema21_5'])}"
                f" ({'cross ' + r['ema_cross'] + ' in last 30m' if r['ema_cross'] else 'no cross in last 30m'})")
    rng = NA if r["range_used"] is None else f"{r['range_used']:.2f}"
    exp = NA if r["exp_lo"] is None else f"{num(r['exp_lo'])}&ndash;{num(r['exp_hi'])}"
    comp = ", ".join(f"{k} {v:+d}" for k, v in r["bias_comp"].items())
    lines = [
        f"<b>Volume:</b> RVOL {rvol_cell(r)}; last-3-bar vol {trend}; up/down vol {ratio(r['ud'])}; spikes (&gt;3x slot avg): {spikes}",
        f"<b>VWAP:</b> {vw}",
        f"<b>Levels:</b> PDH {g('PDH')} / PDL {g('PDL')} / PDC {g('PDC')}; PMH {g('PMH')} / PML {g('PML')}; "
        f"ORH {g('ORH')} / ORL {g('ORL')}; P {g('P')}, R1 {g('R1')}, R2 {g('R2')}, S1 {g('S1')}, S2 {g('S2')}; "
        f"20d {g('20dL')}&ndash;{g('20dH')}; 52w {g('52wL')}&ndash;{g('52wH')}",
        f"<b>Price action:</b> S {lvl(r['sup'], p, atr)} / R {lvl(r['res'], p, atr)}; gap {gap}; "
        f"structure {r['struct'] or NA}; breaks: {', '.join(r['breaks']) or 'none'}",
        f"<b>MAs:</b> 5m {ema5}; daily EMA9 {num(r['d_ema9'])}, EMA21 {num(r['d_ema21'])}, SMA20 {num(r['sma20'])}, "
        f"SMA50 {num(r['sma50'])}, SMA200 {num(r['sma200'])} &rarr; stack {r['stack'] or NA}"
        + (f"; {r['cross']} cross (SMA50/200) in last 10d" if r["cross"] else ""),
        f"<b>RSI:</b> 5m {rsi(r['rsi_5'])}, daily {rsi(r['rsi_d'])}; 5m divergence: {r['div'] or NA}",
        f"<b>ATR:</b> daily {num(atr)} ({ratio(r['atr_pct'])}%), 5m {num(r['atr_5'])}; range used {rng}; expected range left {exp}",
        f"<b>Bias {bias(r)}</b> ({comp}){extra}",
        setup_line("bull", r["watch"]["bull"], "Bullish above"),
        setup_line("bear", r["watch"]["bear"], "Bearish below"),
    ]
    return (f"<h4>{escape(r['sym'])} &mdash; ${num(p)} ({pct(r['day_pct'])})</h4>"
            f'<div class="c">' + "<br>\n".join(lines) + "</div>\n")


def doc(title, note, body):
    return (f"<html><head><meta charset=\"utf-8\">{STYLE}</head><body>"
            f"<h2>{escape(title)}</h2><p><i>{escape(note)}</i></p>{body}"
            "<p><i>Research only, not financial advice. No orders placed.</i></p></body></html>")
