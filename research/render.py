"""Compact HTML email rendering (MAG 7 look: bordered tables, green/red, cards).

Styles live in one <style> block with short class names to keep the HTML small,
because the agent has to pass the whole body to Gmail.
"""
import re
from html import escape

STYLE = ("<style>body{font-family:'Segoe UI',Arial,sans-serif;font-size:13px;color:#222;background:#f4f6f9;margin:0;padding:12px}"
         "h2{margin:0 0 6px;padding:10px 14px;background:#1f2d3d;color:#fff;border-radius:6px;font-size:18px}"
         "h3{margin:18px 0 6px;padding-bottom:3px;border-bottom:2px solid #dfe5ec;color:#1f2d3d;font-size:15px}"
         "h4{margin:0 0 3px;font-size:14px}p,ul{margin:4px 0 8px}li{margin:2px 0}"
         "table{border-collapse:collapse;font-size:12px;margin:4px 0 10px;background:#fff}"
         "td,th{border:1px solid #d5dbe3;padding:4px 6px;text-align:right;white-space:nowrap}"
         "th{background:#1f2d3d;color:#fff;font-weight:600}td.l,th.l{text-align:left}"
         "tr.bu td{background:#eef8f1}tr.bu td:first-child{border-left:4px solid #0a7d2c}"
         "tr.be td{background:#fdf0ee}tr.be td:first-child{border-left:4px solid #c0392b}"
         ".g{color:#0a7d2c;font-weight:600}.r{color:#c0392b;font-weight:600}.z{color:#555}"
         ".p{display:inline-block;padding:1px 8px;border-radius:10px;font-weight:700;font-size:11px}"
         ".pg{background:#d4f0dc;color:#0a7d2c}.pr{background:#fad9d5;color:#c0392b}.pz{background:#e6e9ee;color:#555}"
         ".k{margin:0 0 12px;padding:8px 12px;border-radius:6px;background:#fff;border:1px solid #d5dbe3;border-left:5px solid #9aa5b1}"
         ".kg{border-left-color:#0a7d2c;background:#f6fbf7}.kr{border-left-color:#c0392b;background:#fdf6f5}"
         ".c{font-size:13px;line-height:1.55}.lg{font-size:12px;color:#555}</style>")
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
        ev = f"{tone(r['vwap_event'][0])} VWAP @ {r['vwap_event'][1]} CT" if r["vwap_event"] else "no reclaim/loss"
        vw = (f"{num(r['vwap'])}, px {pct(r['vs_vwap'])} / {ratio(r['vs_vwap_atr'])} ATR; "
              f"&plusmn;1&sigma; {num(r['vwap'] - sd)}&ndash;{num(r['vwap'] + sd)}, "
              f"&plusmn;2&sigma; {num(r['vwap'] - 2 * sd)}&ndash;{num(r['vwap'] + 2 * sd)}; "
              f"slope {tone(r['vwap_slope'])}; {ev}")
    else:
        vw = "thin (OTC / low volume)" if r["thin"] else NA
    gap = NA if r["gap_pct"] is None else (
        f"{r['gap_pct']:+.2f}%" + ("" if r["gap_filled"] is None else f" (filled: {'yes' if r['gap_filled'] else 'no'})"))
    ema5 = NA
    if r["ema_bull"] is not None:
        ema5 = (f"{tone('bullish' if r['ema_bull'] else 'bearish')}: EMA9 {num(r['ema9_5'])} "
                f"{'&gt;' if r['ema_bull'] else '&lt;'} EMA21 {num(r['ema21_5'])}"
                f" ({'cross ' + tone(r['ema_cross']) + ' in last 30m' if r['ema_cross'] else 'no cross in last 30m'})")
    rng = NA if r["range_used"] is None else f"{r['range_used']:.2f}"
    exp = (NA if r["exp_lo"] is None else "none (full ATR used)" if r["exp_lo"] == r["exp_hi"]
           else f"{num(r['exp_lo'])}&ndash;{num(r['exp_hi'])}")
    comp = ", ".join(f'{k} <span class="{cls(v)}">{v:+d}</span>' for k, v in r["bias_comp"].items())
    lines = [
        f"<b>Volume:</b> RVOL {rvol_cell(r)}; last-3-bar vol {trend}; up/down vol {ratio(r['ud'])}; spikes (&gt;3x slot avg): {spikes}",
        f"<b>VWAP:</b> {vw}",
        f"<b>Levels:</b> PDH {g('PDH')} / PDL {g('PDL')} / PDC {g('PDC')}; PMH {g('PMH')} / PML {g('PML')}; "
        f"ORH {g('ORH')} / ORL {g('ORL')}; P {g('P')}, R1 {g('R1')}, R2 {g('R2')}, S1 {g('S1')}, S2 {g('S2')}; "
        f"prior-day volume profile POC {g('POC')}, VAH {g('VAH')}, VAL {g('VAL')}; PWH {g('PWH')} / PWL {g('PWL')}; "
        f"20d {g('20dL')}&ndash;{g('20dH')}; 52w {g('52wL')}&ndash;{g('52wH')}",
        f"<b>Price action:</b> S {lvl(r['sup'], p, atr)} / R {lvl(r['res'], p, atr)}; gap {gap}; "
        f"structure {tone(r['struct'])}; breaks: {', '.join(r['breaks']) or 'none'}",
        f"<b>Open &amp; gap:</b> {orb_text(r)}; {gap_text(r)}",
        f"<b>Intraday RS:</b> {rs_text(r)}",
        f"<b>MAs:</b> 5m {ema5}; daily EMA9 {num(r['d_ema9'])}, EMA21 {num(r['d_ema21'])}, SMA20 {num(r['sma20'])}, "
        f"SMA50 {num(r['sma50'])}, SMA200 {num(r['sma200'])} &rarr; stack {tone(r['stack'])}"
        + (f"; {tone(r['cross'])} cross (SMA50/200) in last 10d" if r["cross"] else ""),
        f"<b>RSI:</b> 5m {rsi(r['rsi_5'])}, daily {rsi(r['rsi_d'])}; 5m divergence: {tone(r['div'])}",
        f"<b>Momentum:</b> 5m MACD(12,26,9) hist {num(r.get('macd_hist'), 3)} ({tone_pair(r.get('macd_state'))})"
        + (f", {tone(r['macd_cross'])} cross in last 30m" if r.get("macd_cross") else "")
        + f"; ADX {adx_cell(r)} (+DI {num(r.get('pdi'), 0)} / &minus;DI {num(r.get('mdi'), 0)}) &rarr; {tone(adx_trend(r))}"
        + f"; squeeze {sqz_text(r.get('sqz'))}",
        f"<b>Daily pattern:</b> " + (f"{escape(r['pattern'])} (no extra range in testing)" if r.get("pattern") else "none"),
        f"<b>ATR:</b> daily {num(atr)} ({ratio(r['atr_pct'])}%), 5m {num(r['atr_5'])}; range used {rng}; expected range left {exp}",
        f"<b>In play:</b> {r.get('in_play', 0)}/4" + (f" ({', '.join(r['in_play_why'])})" if r.get("in_play_why") else "")
,
        f"<b>Bias {bias(r)}</b> ({comp}); confirmations {r.get('conf', 0)}/2 (MACD, ADX/DMI){extra}",
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


_PILL_CSS = "display:inline-block;padding:1px 8px;border-radius:10px;font-weight:bold;font-size:11px;"
# Gmail drops the <style> block, every class attribute and all background colours, so each class is
# written inline as well and no text relies on a background to be readable (no white-on-dark text).
INLINE = {
    "g": "color:#0a7d2c;font-weight:bold", "r": "color:#c0392b;font-weight:bold", "z": "color:#555",
    "p pg": _PILL_CSS + "background:#d4f0dc;color:#0a7d2c", "p pr": _PILL_CSS + "background:#fad9d5;color:#c0392b",
    "p pz": _PILL_CSS + "background:#e6e9ee;color:#555",
    "k": "margin:0 0 12px;padding:8px 12px;border:1px solid #d5dbe3;border-left:5px solid #9aa5b1;border-radius:6px;background:#fff",
    "c": "font-size:13px;line-height:1.55", "lg": "font-size:12px;color:#555",
}
_TAGS = {
    "<h2>": '<h2 style="margin:0 0 6px;padding:8px 0;border-bottom:3px solid #1f2d3d;color:#1f2d3d;font-size:18px">',
    "<h3>": '<h3 style="margin:18px 0 6px;padding-bottom:3px;border-bottom:2px solid #dfe5ec;color:#1f2d3d;font-size:15px">',
    "<h4>": '<h4 style="margin:0 0 3px;font-size:14px">',
    '<table border="1">': '<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-size:12px;'
                          'margin:4px 0 10px;background:#fff;border-color:#d5dbe3">',
    "<th>": '<th align="right" style="color:#1f2d3d;border-bottom:2px solid #1f2d3d">',
    '<th class="l">': '<th align="left" style="color:#1f2d3d;border-bottom:2px solid #1f2d3d">',
    "<td>": '<td align="right" style="white-space:nowrap">',
    '<td class="l">': '<td align="left">',
}


def inline(html):
    """Copy every class style into an inline style attribute (email clients such as Gmail strip <style>)."""
    for k, v in _TAGS.items():
        html = html.replace(k, v)
    return re.sub(r'class="([^"]*)"', lambda m: f'class="{m.group(1)}" style="{INLINE[m.group(1).strip()]}"'
                  if m.group(1).strip() in INLINE else m.group(0), html)


def doc(title, note, body):
    return (f"<html><head><meta charset=\"utf-8\">{STYLE}</head><body>"
            '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:13px;color:#222">'
            + inline(f"<h2>{escape(title)}</h2><p><i>{escape(note)}</i></p>{LEGEND}{words_only(body)}")
            + "<p><i>Research only, not financial advice. No orders placed.</i></p></div></body></html>")
