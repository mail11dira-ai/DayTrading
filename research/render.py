"""Compact HTML email rendering (MAG 7 look: bordered tables, green/red, cards).

Rendering uses short class names; doc() turns them into short inline styles because Gmail strips <style>
blocks, class attributes and backgrounds. Keep the HTML small: the agent passes the whole body to Gmail.
"""
import re
from html import escape

NA = "n/a"
PILL = re.compile(r'class="p p(\w)"')
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


BULL_WORDS = {"holding", "fired up", "trending up", "bull", "bullish", "uptrend", "golden", "reclaimed", "up", "bull above", "bullish above"}
BEAR_WORDS = {"fired down", "trending down", "bear", "bearish", "downtrend", "death", "lost", "down", "bear below", "bearish below"}


def tone(text):
    """Wrap a bullish word in green and a bearish word in red; other text unchanged."""
    if text is None:
        return NA
    k = str(text).strip().lower()
    c = "g" if k in BULL_WORDS else "r" if k in BEAR_WORDS else None
    return f'<span class="{c}">{text}</span>' if c else str(text)


def tone_pair(text):
    """'bullish, expanding' -> colors the first word."""
    if not text:
        return NA
    head, _, tail = text.partition(", ")
    return tone(head) + (f", {tail}" if tail else "")


def pill(text, c):
    return f'<span class="p p{c}">{text}</span>'


def score(x, d=1):
    """Signed average bias as a pill: green >= +0.5, red <= -0.5, else grey."""
    if x is None:
        return NA
    return pill(f"{x:+.{d}f}", "g" if x >= 0.5 else "r" if x <= -0.5 else "z")


def bias(r):
    c = {"BULLISH": "g", "BEARISH": "r"}.get(r["bias_label"], "z")
    return pill(f'{r["bias"]:+d} {r["bias_label"]}', c)


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


def table(headers, rows, left=1, tint=None):
    """tint: index of the cell whose green/red colour shades the row (default: the row's first bias pill)."""
    h = "".join(f'<th class="l">{x}</th>' if i < left else f"<th>{x}</th>" for i, x in enumerate(headers))
    body = []
    for row in rows:
        if isinstance(row, str):
            body.append(row)
            continue
        m = (re.search(r'class="([gr])"', str(row[tint])) if tint is not None
             else PILL.search("".join(map(str, row))))
        tr = {"g": ' class="bu"', "r": ' class="be"'}.get(m.group(1), "") if m else ""
        body.append(f"<tr{tr}>" + "".join(
            f'<td class="l">{x}</td>' if i < left else f"<td>{x}</td>" for i, x in enumerate(row)) + "</tr>\n")
    out = f'<table border="1"><tr>{h}</tr>{"".join(body)}</table>'
    return SPAN_TD.sub(r'<td class="\1">\2</td>', out)


def adx_trend(r):
    """'trending up/down' (ADX >= 25), 'developing up/down' (20-25) or 'choppy'."""
    a, p, m = r.get("adx"), r.get("pdi"), r.get("mdi")
    if None in (a, p, m):
        return None
    if a < 20:
        return "choppy"
    d = "up" if p > m else "down"
    return f"{'trending' if a >= 25 else 'developing'} {d}"


def adx_cell(r):
    """ADX value colored by DI direction once ADX >= 20 (trend strong enough to matter)."""
    a = r.get("adx")
    if a is None:
        return NA
    t = adx_trend(r)
    if t == "choppy":
        return f"{a:.0f}"
    return f'<span class="{"g" if t.endswith("up") else "r"}">{a:.0f}{" &uarr;" if t.endswith("up") else " &darr;"}</span>'


def sqz_text(q):
    if not q:
        return NA
    state, k = q
    if state == "on":
        return f"ON for {k} bar{'s' if k != 1 else ''} (compressed; next hour was usually quieter, not a breakout)"
    if state.startswith("fired"):
        return f"{tone(state)} {k} bar{'s' if k != 1 else ''} ago"
    return "off"


def orb_text(r):
    """Opening ranges (5/15/30 min) and the volume-confirmed 15-minute breakout state, coloured by direction."""
    rg = r.get("or_ranges") or {}
    base = rg.get(15)
    shown = [(m, v) for m, v in rg.items() if m == 15 or v != base]  # 5/30-minute ranges only when they differ
    ranges = "; ".join(f"OR{m} {num(h)}/{num(l)}" for m, (h, l) in shown) or "OR n/a (range not complete)"
    o = r.get("orb")
    if not o:
        return ranges
    if o["state"] == "inside":
        return f"{ranges}; ORB: inside the 15m range"
    vol = f"{o['volx']:.1f}x volume" if o["volx"] is not None else "volume n/a"
    up = o["dir"] == "up"
    word = {"confirmed": f"ORB {o['dir']} confirmed", "weak": f"ORB {o['dir']} weak (light volume)",
            "failed": f"ORB {o['dir']} FAILED (back inside)"}[o["state"]]
    c = {"confirmed": "g" if up else "r", "weak": "z", "failed": "r" if up else "g"}[o["state"]]
    return f'{ranges}; <span class="{c}">{word}</span> ({vol} @ {o["time"]} CT)'


def gap_text(r):
    """Pre-market volume vs normal and the gap classification."""
    pm = NA if r.get("pm_rvol") is None else f"{r['pm_rvol']:.1f}x normal"
    gp = NA if r.get("gap_pct") is None else f"{r['gap_pct']:+.2f}%" + (
        "" if r.get("gap_atr") is None else f" ({r['gap_atr']:+.2f} ATR)")
    q = r.get("gap_q")
    lab = "no meaningful gap (&lt; 0.3 ATR)"
    if q:
        kind, d = q
        lab = {("go", "up"): '<span class="g">gap-and-go up</span>', ("go", "down"): '<span class="r">gap-and-go down</span>',
               ("fade", "up"): '<span class="r">fade risk (gap up may retrace)</span>',
               ("fade", "down"): '<span class="g">fade risk (gap down may bounce)</span>',
               ("gap", "up"): f'<span class="z">gap up, no volume edge</span>',
               ("gap", "down"): f'<span class="z">gap down, no volume edge</span>'}[(kind, d)]
    return f"pre-mkt vol {pm}; gap {gp} &rarr; {lab}"


def rs_text(r):
    """Intraday relative strength vs QQQ over 15 / 30 minutes."""
    if r.get("rs30") is None:
        return NA
    s30 = r["rs30"]
    lab = '<span class="g">leading</span>' if s30 >= 0.3 else '<span class="r">lagging</span>' if s30 <= -0.3 else "in line"
    p15 = NA if r.get("rs15") is None else pct(r["rs15"])
    return f"15m {p15} / 30m {pct(s30)} vs QQQ &rarr; {lab}"


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
    return (f"{word} {num(s['trigger'])} ({escape(s['trigger_label'])}) &rarr; {num(s['target'])}; "
            f"invalid {num(s['stop'])}; R/R {ratio(s['rr'])}{poor}")


def card(r, extra="", full_levels=False, brief=False):
    p, atr, lv = r["price"], r["atr"], r["levels"]
    g = lambda k: num(lv.get(k))
    spikes = ", ".join(f"{t} {m:.1f}x {d}" for t, m, d in r["spikes"][:2]) or "none"
    trend = NA if r["vol_trend"] is None else f"{r['vol_trend']:.1f}x ({'rising' if r['vol_trend'] >= 1 else 'falling'})"
    if r["vwap"] and not r["thin"]:
        ev = f"; {tone(r['vwap_event'][0])} @ {r['vwap_event'][1]}" if r["vwap_event"] else ""
        vw = f"{num(r['vwap'])}, px {pct(r['vs_vwap'])}, slope {tone(r['vwap_slope'])}{ev}"
    else:
        vw = "thin (OTC / low volume)" if r["thin"] else NA
    ema5 = NA if r["ema_bull"] is None else tone("bullish" if r["ema_bull"] else "bearish") + (
        f" (cross {tone(r['ema_cross'])} in last 30m)" if r["ema_cross"] else "")
    rng = NA if r["range_used"] is None else f"{r['range_used']:.2f}"
    comp = ", ".join(f"{k} {v:+d}" for k, v in r["bias_comp"].items())
    if brief:  # short card: volume, VWAP, open / gap, range and in-play, bias, setup
        lines = [
            f"<b>Volume:</b> RVOL {rvol_cell(r)}; spikes: {spikes}",
            f"<b>VWAP:</b> {vw}",
            f"<b>Open &amp; gap:</b> {orb_text(r)}; {gap_text(r)}",
            f"<b>Range:</b> ATR {ratio(r['atr_pct'])}%, used {rng}; <b>in play {r.get('in_play', 0)}/4</b>",
            f"<b>Bias {bias(r)}</b> ({comp}); confirmations {r.get('conf', 0)}/2{extra}",
            setup_line("bull", r["watch"]["bull"], '<span class="g">Bullish above</span>'),
            setup_line("bear", r["watch"]["bear"], '<span class="r">Bearish below</span>'),
        ]
    else:
        lines = [
            f"<b>Volume:</b> RVOL {rvol_cell(r)}; last 3 bars {trend}; spikes: {spikes}",
            f"<b>VWAP:</b> {vw}",
            f"<b>Levels:</b> PDH {g('PDH')} / PDL {g('PDL')} / PDC {g('PDC')}; PMH {g('PMH')} / PML {g('PML')}; "
            f"S {lvl(r['sup'], p, atr)} / R {lvl(r['res'], p, atr)}",
            f"<b>Open &amp; gap:</b> {orb_text(r)}; {gap_text(r)}",
        ] + ([
            f"<b>Index levels:</b> pivots P {g('P')}, R1 {g('R1')}, R2 {g('R2')}, S1 {g('S1')}, S2 {g('S2')}; "
            f"prior-day POC {g('POC')}, VAH {g('VAH')}, VAL {g('VAL')}; PWH {g('PWH')} / PWL {g('PWL')}; "
            f"ORH {g('ORH')} / ORL {g('ORL')}; 20d {g('20dL')}&ndash;{g('20dH')}",
        ] if full_levels else []) + [
            f"<b>Intraday RS:</b> {rs_text(r)}",
            f"<b>Trend:</b> 5m EMA9/21 {ema5}; daily stack {tone(r['stack'])}"
            + (f", {tone(r['cross'])} cross" if r["cross"] else "") + f"; RSI 5m {rsi(r['rsi_5'])} / daily {rsi(r['rsi_d'])}",
            f"<b>Range:</b> ATR {ratio(r['atr_pct'])}%, used {rng}; <b>in play {r.get('in_play', 0)}/4</b>"
            + (f" ({', '.join(r['in_play_why'])})" if r.get("in_play_why") else ""),
            f"<b>Bias {bias(r)}</b> ({comp}); confirmations {r.get('conf', 0)}/2{extra}",
            setup_line("bull", r["watch"]["bull"], '<span class="g">Bullish above</span>'),
            setup_line("bear", r["watch"]["bear"], '<span class="r">Bearish below</span>'),
        ]
    k = {"BULLISH": "kg", "BEARISH": "kr"}.get(r["bias_label"], "")
    return (f'<div class="k {k}"><h4>{escape(r["sym"])} &mdash; ${num(p)} ({pct(r["day_pct"])}) {bias(r)}</h4>'
            f'<div class="c">' + "<br>\n".join(lines) + "</div></div>\n")


LEGEND = (f'<p class="lg">{pill("Bullish", "g")} {pill("Bearish", "r")} {pill("Neutral", "z")} '
          "&nbsp;only the words Bullish (green) and Bearish (red) are coloured</p>")

_TONE = re.compile(r'<span class="[grz]">([^<]*)</span>')
_PILLS = re.compile(r'<span class="p p\w">([^<]*)</span>')
_WORD = re.compile(r"\b(bullish|bearish)\b", re.I)


def _pill_by_word(m):
    t = m.group(1).upper()
    return pill(m.group(1), "g" if "BULLISH" in t else "r" if "BEARISH" in t else "z")


def words_only(html):
    """Colour rule (2026-10-20): only the words Bullish (green) and Bearish (red) carry colour.

    Strips every other green/red/grey tint (numbers, up/down words, row and card shading) and
    re-colours each bullish/bearish word; bias pills stay coloured only when they say BULLISH/BEARISH.
    """
    html = re.sub(r'<tr class="b[ue]">', "<tr>", html)
    html = re.sub(r'class="k k[gr]"', 'class="k"', html)
    html = re.sub(r'<td class="[grz]">', "<td>", html)
    html = _TONE.sub(r"\1", html)
    html = _PILLS.sub(_pill_by_word, html)
    out, in_pill = [], False
    for tok in re.split(r"(<[^>]+>)", html):
        if tok.startswith("<"):
            in_pill = tok.startswith('<span class="p ') or (in_pill and tok != "</span>")
        elif not in_pill:
            tok = _WORD.sub(lambda m: f'<span class="{"g" if m.group(1).lower() == "bullish" else "r"}">{m.group(1)}</span>', tok)
        out.append(tok)
    return "".join(out)


_PILL_CSS = "font-weight:bold;"
# Gmail drops the <style> block, every class attribute and all background colours, so each class is
# written inline as well and no text relies on a background to be readable (no white-on-dark text).
INLINE = {
    "g": "color:#0a7d2c;font-weight:bold", "r": "color:#c0392b;font-weight:bold", "z": "color:#555",
    "p pg": _PILL_CSS + "color:#0a7d2c", "p pr": _PILL_CSS + "color:#c0392b", "p pz": _PILL_CSS + "color:#555",
    "k": "margin:0 0 10px;padding:6px 10px;border:1px solid #d5dbe3", "lg": "font-size:12px;color:#555",
}
_TAGS = {
    "<h2>": '<h2 style="margin:0 0 6px;padding:8px 0;border-bottom:3px solid #1f2d3d;color:#1f2d3d;font-size:18px">',
    "<h3>": '<h3 style="margin:18px 0 6px;padding-bottom:3px;border-bottom:2px solid #dfe5ec;color:#1f2d3d;font-size:15px">',
    "<h4>": '<h4 style="margin:0 0 3px;font-size:14px">',
    '<table border="1">': '<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-size:12px;'
                          'margin:4px 0 10px;border-color:#d5dbe3">',
    "<th>": '<th align="right" style="color:#1f2d3d;border-bottom:2px solid #1f2d3d">',
    '<th class="l">': '<th align="left" style="color:#1f2d3d;border-bottom:2px solid #1f2d3d">',
    "<td>": '<td align="right" nowrap>',
    '<td class="l">': '<td align="left">',
}


def inline(html):
    """Copy every class style into an inline style attribute (email clients such as Gmail strip <style>)."""
    for k, v in _TAGS.items():
        html = html.replace(k, v)
    return re.sub(r' class="([^"]*)"', lambda m: f' style="{INLINE[m.group(1).strip()]}"'
                  if m.group(1).strip() in INLINE else "", html)


def doc(title, note, body):
    return ("<html><head><meta charset=\"utf-8\"></head><body>"
            '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:13px;color:#222">'
            + inline(f"<h2>{escape(title)}</h2><p><i>{escape(note)}</i></p>{LEGEND}{words_only(body)}")
            + "<p><i>Research only, not financial advice. No orders placed.</i></p></div></body></html>")
