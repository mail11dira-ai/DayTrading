"""Technical-analysis primitives. Pure functions over plain lists, no I/O.

Conventions: series are oldest-first; functions return None where a value
cannot be computed instead of inventing one.
"""
import math


def sma(values, n):
    """Simple moving average of the last n values (None if too short)."""
    if n <= 0 or len(values) < n:
        return None
    return sum(values[-n:]) / n


def sma_series(values, n):
    out = [None] * len(values)
    for i in range(n - 1, len(values)):
        out[i] = sum(values[i - n + 1:i + 1]) / n
    return out


def ema_series(values, n):
    """EMA with alpha 2/(n+1), seeded with the SMA of the first n values."""
    out = [None] * len(values)
    if len(values) < n:
        return out
    k = 2 / (n + 1)
    e = sum(values[:n]) / n
    out[n - 1] = e
    for i in range(n, len(values)):
        e = values[i] * k + e * (1 - k)
        out[i] = e
    return out


def rsi_series(closes, n=14):
    """Wilder RSI. First value at index n."""
    out = [None] * len(closes)
    if len(closes) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    out[n] = _rsi(ag, al)
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out[i] = _rsi(ag, al)
    return out


def _rsi(ag, al):
    if al == 0:
        return 100.0 if ag > 0 else 50.0
    return 100 - 100 / (1 + ag / al)


def atr_series(highs, lows, closes, n=14):
    """Wilder ATR. TR[0] = H-L; first ATR = mean of the first n TRs."""
    m = len(closes)
    out = [None] * m
    if m < n:
        return out
    tr = []
    for i in range(m):
        hl = highs[i] - lows[i]
        if i == 0:
            tr.append(hl)
        else:
            pc = closes[i - 1]
            tr.append(max(hl, abs(highs[i] - pc), abs(lows[i] - pc)))
    a = sum(tr[:n]) / n
    out[n - 1] = a
    for i in range(n, m):
        a = (a * (n - 1) + tr[i]) / n
        out[i] = a
    return out


def vwap_series(bars):
    """Cumulative VWAP (typical price) and volume-weighted std dev per bar.

    bars: list of dicts with h, l, c, v. Returns (vwap list, sd list); None
    until volume > 0.
    """
    pv = vv = pv2 = 0.0
    vw, sd = [], []
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3
        pv += tp * b["v"]
        pv2 += tp * tp * b["v"]
        vv += b["v"]
        if vv > 0:
            m = pv / vv
            vw.append(m)
            sd.append(math.sqrt(max(pv2 / vv - m * m, 0.0)))
        else:
            vw.append(None)
            sd.append(None)
    return vw, sd


def vwap_event(closes, vwaps):
    """Last 'reclaimed'/'lost' VWAP event: a cross that then held 2+ bars.

    Returns (event, index_of_first_bar_on_new_side) or (None, None).
    """
    side = []
    for c, v in zip(closes, vwaps):
        side.append(None if v is None else (1 if c > v else -1 if c < v else 0))
    last = (None, None)
    for i in range(1, len(side) - 1):
        a, b, c = side[i - 1], side[i], side[i + 1]
        if a == -1 and b == 1 and c == 1:
            last = ("reclaimed", i)
        elif a == 1 and b == -1 and c == -1:
            last = ("lost", i)
    return last


def floor_pivots(h, l, c):
    p = (h + l + c) / 3
    return {"P": p, "R1": 2 * p - l, "S1": 2 * p - h, "R2": p + (h - l), "S2": p - (h - l)}


def round_step(price):
    """A 'nice' round-number step near price/50 (1, 2.5 or 5 x 10^k)."""
    if price <= 0:
        return None
    raw = price / 50
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def round_levels(price, atr):
    """Round numbers within 1 ATR of price."""
    step = round_step(price)
    if step is None or not atr:
        return []
    lo, hi = price - atr, price + atr
    k = math.ceil(lo / step)
    out = []
    while k * step <= hi:
        lvl = round(k * step, 6)
        out.append((lvl, f"RN{_fmt_level(lvl)}"))
        k += 1
    return out


def _fmt_level(x):
    return f"{x:g}"


def merge_zones(levels, atr, price, merge_atr=0.10, drop_atr=0.15):
    """Merge levels within merge_atr*ATR into zones (midpoint, joined labels),
    then drop zones within drop_atr*ATR of price. Returns sorted [(px, label)].
    """
    pts = sorted((p, lab) for p, lab in levels if p is not None and p > 0)
    if not pts or not atr:
        return []
    groups = [[pts[0]]]
    for p, lab in pts[1:]:
        if p - groups[-1][0][0] <= merge_atr * atr:
            groups[-1].append((p, lab))
        else:
            groups.append([(p, lab)])
    zones = []
    for g in groups:
        mid = sum(p for p, _ in g) / len(g)
        labels = []
        for _, lab in g:
            if lab not in labels:
                labels.append(lab)
        zones.append((mid, "/".join(labels)))
    return [z for z in zones if abs(z[0] - price) > drop_atr * atr]


def nearest(zones, price):
    below = [z for z in zones if z[0] < price]
    above = [z for z in zones if z[0] > price]
    return (below[-1] if below else None), (above[0] if above else None)


def watch_levels(price, atr, zones, max_target_atr=2.0):
    """Bullish/bearish watch levels per the WATCH LEVELS rules. A target level must lie
    0.5-max_target_atr daily ATRs beyond the trigger (a day-trading horizon); otherwise the
    target is the +/-0.75 ATR projection.

    Each side: dict(trigger, trigger_label, target, target_label,
    stop, stop_label, reward_atr, risk_atr, rr) or None.
    """
    if not atr or not zones:
        return {"bull": None, "bear": None}
    above = [z for z in zones if z[0] > price]
    below = [z for z in zones if z[0] < price][::-1]  # nearest first
    out = {"bull": None, "bear": None}
    if above:
        trig, tl = above[0]
        tgt = next((z for z in above[1:] if z[0] >= trig + 0.5 * atr), None)
        tgt = tgt if (tgt and tgt[0] <= trig + max_target_atr * atr) else None
        tgt = tgt or (trig + 0.75 * atr, "ATR projection")
        stop = next((z for z in below if z[0] <= trig - 0.25 * atr), None)
        stop = stop or (trig - 0.5 * atr, "ATR stop")
        out["bull"] = _side(trig, tl, tgt, stop, atr)
    if below:
        trig, tl = below[0]
        tgt = next((z for z in below[1:] if z[0] <= trig - 0.5 * atr), None)
        tgt = tgt if (tgt and tgt[0] >= trig - max_target_atr * atr) else None
        tgt = tgt or (trig - 0.75 * atr, "ATR projection")
        stop = next((z for z in above if z[0] >= trig + 0.25 * atr), None)
        stop = stop or (trig + 0.5 * atr, "ATR stop")
        out["bear"] = _side(trig, tl, tgt, stop, atr)
    return out


def _side(trig, tl, tgt, stop, atr):
    reward = abs(tgt[0] - trig) / atr
    risk = abs(trig - stop[0]) / atr
    return {"trigger": trig, "trigger_label": tl, "target": tgt[0], "target_label": tgt[1],
            "stop": stop[0], "stop_label": stop[1], "reward_atr": reward,
            "risk_atr": risk, "rr": reward / risk if risk else None}


def structure(highs, lows):
    """Intraday structure from 1-bar swing points: 'uptrend', 'downtrend',
    'range', or None when there are fewer than two swing highs and lows."""
    ph = [highs[i] for i in range(1, len(highs) - 1)
          if highs[i] > highs[i - 1] and highs[i] >= highs[i + 1]]
    pl = [lows[i] for i in range(1, len(lows) - 1)
          if lows[i] < lows[i - 1] and lows[i] <= lows[i + 1]]
    if len(ph) < 2 or len(pl) < 2:
        return None
    if ph[-1] > ph[-2] and pl[-1] > pl[-2]:
        return "uptrend"
    if ph[-1] < ph[-2] and pl[-1] < pl[-2]:
        return "downtrend"
    return "range"


def divergence(highs, lows, rsis, window=12):
    """RSI divergence over the last `window` bars (two halves compared)."""
    if len(highs) < window or any(r is None for r in rsis[-window:]):
        return None
    h, l, r = highs[-window:], lows[-window:], rsis[-window:]
    half = window // 2
    i1 = max(range(half), key=lambda i: h[i])
    i2 = max(range(half, window), key=lambda i: h[i])
    if h[i2] > h[i1] and r[i2] < r[i1]:
        return "bearish"
    j1 = min(range(half), key=lambda i: l[i])
    j2 = min(range(half, window), key=lambda i: l[i])
    if l[j2] < l[j1] and r[j2] > r[j1]:
        return "bullish"
    return "none"


def ma_stack(price, ema9, ema21, sma50):
    if None in (price, ema9, ema21, sma50):
        return None
    if price > ema9 > ema21 > sma50:
        return "bullish"
    if price < ema9 < ema21 < sma50:
        return "bearish"
    return "mixed"


def last_cross(fast, slow, lookback):
    """'golden'/'death' if fast crossed slow within the last `lookback` bars."""
    pairs = [(f, s) for f, s in zip(fast, slow) if f is not None and s is not None]
    pairs = pairs[-(lookback + 1):]
    for i in range(len(pairs) - 1, 0, -1):
        (f0, s0), (f1, s1) = pairs[i - 1], pairs[i]
        if f0 <= s0 and f1 > s1:
            return "golden"
        if f0 >= s0 and f1 < s1:
            return "death"
    return None


def bias_score(vwap_side, ema_bull, stack, rsi5, rvol, ud_ratio, struct, vwap_ok=True):
    """Deterministic -6..+6 bias. Returns (score, label, components dict)."""
    comp = {}
    comp["vwap"] = 0 if (vwap_side is None or not vwap_ok) else (1 if vwap_side > 0 else -1 if vwap_side < 0 else 0)
    comp["ema"] = 0 if ema_bull is None else (1 if ema_bull else -1)
    comp["stack"] = {"bullish": 1, "bearish": -1}.get(stack, 0)
    if rsi5 is None:
        comp["rsi"] = 0
    elif 55 <= rsi5 <= 70:
        comp["rsi"] = 1
    elif 30 <= rsi5 <= 45:
        comp["rsi"] = -1
    else:
        comp["rsi"] = 0
    if rvol is not None and ud_ratio is not None and rvol > 1.2:
        comp["vol"] = 1 if ud_ratio > 1 else -1 if ud_ratio < 1 else 0
    else:
        comp["vol"] = 0
    comp["struct"] = {"uptrend": 1, "downtrend": -1}.get(struct, 0)
    score = sum(comp.values())
    label = "BULLISH" if score >= 3 else "BEARISH" if score <= -3 else "NEUTRAL"
    return score, label, comp


def macd_series(closes, fast=12, slow=26, signal=9):
    """MACD line, signal line and histogram (None until computable)."""
    ef, es = ema_series(closes, fast), ema_series(closes, slow)
    line = [None if (a is None or b is None) else a - b for a, b in zip(ef, es)]
    vals = [x for x in line if x is not None]
    sig_vals = ema_series(vals, signal)
    sig = [None] * (len(line) - len(vals)) + sig_vals
    hist = [None if (m is None or s is None) else m - s for m, s in zip(line, sig)]
    return line, sig, hist


def adx_series(highs, lows, closes, n=14):
    """Wilder ADX with +DI / -DI. Returns (adx, pdi, mdi) lists; ADX first at index 2n-1."""
    m = len(closes)
    adx, pdi, mdi = [None] * m, [None] * m, [None] * m
    if m <= 2 * n:
        return adx, pdi, mdi
    tr, pdm, mdm = [], [], []
    for i in range(1, m):
        up, dn = highs[i] - highs[i - 1], lows[i - 1] - lows[i]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    st, sp, sm = sum(tr[:n]), sum(pdm[:n]), sum(mdm[:n])
    dxs = []
    for j in range(n - 1, len(tr)):
        if j >= n:
            st, sp, sm = st - st / n + tr[j], sp - sp / n + pdm[j], sm - sm / n + mdm[j]
        p, q = (100 * sp / st, 100 * sm / st) if st else (0.0, 0.0)
        pdi[j + 1], mdi[j + 1] = p, q
        dxs.append(100 * abs(p - q) / (p + q) if p + q else 0.0)
        if len(dxs) == n:
            a = sum(dxs) / n
            adx[j + 1] = a
        elif len(dxs) > n:
            a = (a * (n - 1) + dxs[-1]) / n
            adx[j + 1] = a
    return adx, pdi, mdi


def squeeze(highs, lows, closes, n=20, bb=2.0, kc=1.5, lookback=6):
    """TTM-style squeeze: Bollinger(n, bb) inside Keltner(SMA n +/- kc*ATR n).

    Returns ('on', bars_on) | ('fired up'/'fired down', bars_ago) | ('off', 0) | None.
    """
    m = len(closes)
    if m < n + lookback + 1:
        return None
    atr = atr_series(highs, lows, closes, n)
    states = []
    for i in range(m - lookback - 1, m):
        w = closes[i - n + 1:i + 1]
        mu = sum(w) / n
        sd = math.sqrt(sum((x - mu) ** 2 for x in w) / n)
        a = atr[i]
        states.append(a is not None and mu + bb * sd < mu + kc * a and mu - bb * sd > mu - kc * a)
    if states[-1]:
        k = 0
        for s in reversed(states):
            if not s:
                break
            k += 1
        return ("on", k)
    for ago in range(1, len(states)):
        if states[-1 - ago]:
            mu = sum(closes[-n:]) / n
            return ("fired up" if closes[-1] > mu else "fired down", ago)
    return ("off", 0)


def volume_profile(bars, step, value_area=0.70):
    """POC / VAH / VAL from bars (dicts h, l, v); each bar's volume is spread
    evenly over the price bins its high-low range touches."""
    if not bars or not step or step <= 0:
        return None
    vol = {}
    for b in bars:
        lo, hi = math.floor(b["l"] / step), math.floor(b["h"] / step)
        k = hi - lo + 1
        for i in range(lo, hi + 1):
            vol[i] = vol.get(i, 0.0) + b["v"] / k
    total = sum(vol.values())
    if total <= 0:
        return None
    poc = max(vol, key=lambda i: (vol[i], -i))
    lo = hi = poc
    acc = vol[poc]
    while acc < value_area * total and (lo > min(vol) or hi < max(vol)):
        below = vol.get(lo - 1, 0.0) if lo > min(vol) else -1
        above = vol.get(hi + 1, 0.0) if hi < max(vol) else -1
        if above >= below:
            hi += 1
            acc += max(above, 0)
        else:
            lo -= 1
            acc += max(below, 0)
    mid = lambda i: (i + 0.5) * step
    return {"POC": mid(poc), "VAH": (hi + 1) * step, "VAL": lo * step}


def daily_pattern(highs, lows, n=7):
    """Compression patterns of the LAST completed daily bar: 'inside day', 'NR7', both, or None."""
    out = []
    if len(highs) >= 2 and highs[-1] <= highs[-2] and lows[-1] >= lows[-2]:
        out.append("inside day")
    if len(highs) >= n:
        rng = [h - l for h, l in zip(highs[-n:], lows[-n:])]
        if rng[-1] <= min(rng[:-1]):
            out.append(f"NR{n}")
    return " + ".join(out) or None


def confirmations(bias, macd_hist, macd_prev, adx, pdi, mdi, adx_min=20):
    """How many momentum/trend filters agree with the bias direction (0-2):
    MACD histogram on the bias side and expanding; ADX >= adx_min with DI on the bias side."""
    if not bias:
        return 0
    s = 1 if bias > 0 else -1
    n = 0
    if macd_hist is not None and macd_prev is not None and macd_hist * s > 0 and abs(macd_hist) >= abs(macd_prev):
        n += 1
    if None not in (adx, pdi, mdi) and adx >= adx_min and (pdi - mdi) * s > 0:
        n += 1
    return n


def window_return(closes, first_open, n):
    """% change over the last n bars; if the series is shorter than n+1, measured from the first open."""
    if not closes or not first_open:
        return None
    base = closes[-1 - n] if len(closes) > n else first_open
    return (closes[-1] / base - 1) * 100 if base else None


def orb_status(bars, n, slot_avg, vol_mult=1.5):
    """Opening-range breakout with volume confirmation, judged on the CURRENT position.

    bars: one session's regular bars, oldest first, dicts with t (datetime), h, l, c, v.
    n: bars in the opening range (3 = the first 15 minutes). slot_avg: {time-of-day: average bar volume}.
    Returns None until the range is complete, else dict(state, dir, time, volx, hi, lo):
      'inside'    no bar has closed outside the range
      'confirmed' price is outside the range and the bar that started this breakout had >= vol_mult x normal volume
      'weak'      price is outside but the breakout bar had light (or unknown) volume
      'failed'    price broke out earlier but is back inside the range (dir = the last breakout direction)
    """
    if len(bars) <= n:
        return None
    hi, lo = max(b["h"] for b in bars[:n]), min(b["l"] for b in bars[:n])
    side = [("up" if b["c"] > hi else "down" if b["c"] < lo else None) for b in bars[n:]]
    rest = bars[n:]
    last = side[-1]
    if last is None:
        prior = [d for d in side if d]
        if not prior:
            return {"state": "inside", "dir": None, "time": None, "volx": None, "hi": hi, "lo": lo}
        i = max(k for k, d in enumerate(side) if d)  # most recent outside close
        while i > 0 and side[i - 1] == side[i]:
            i -= 1
        d = side[max(k for k, x in enumerate(side) if x)]
        return {"state": "failed", "dir": d, "time": rest[i]["t"].strftime("%H:%M"),
                "volx": _volx(rest[i], slot_avg), "hi": hi, "lo": lo}
    i = len(side) - 1
    while i > 0 and side[i - 1] == last:  # first bar of the current outside streak
        i -= 1
    volx = _volx(rest[i], slot_avg)
    state = "confirmed" if volx is not None and volx >= vol_mult else "weak"
    return {"state": state, "dir": last, "time": rest[i]["t"].strftime("%H:%M"), "volx": volx, "hi": hi, "lo": lo}


def _volx(bar, slot_avg):
    base = slot_avg.get(bar["t"].time())
    return bar["v"] / base if base else None


def gap_quality(gap_atr, pm_rvol, holding):
    """Classify an opening gap: ('go'|'fade'|'gap', 'up'|'down') or None for a gap under 0.3 ATR.

    go   = gap of >= 0.3 ATR on >= 2x normal pre-market volume and still holding its side;
    fade = a gap of >= 1 ATR that lacks that volume or is not holding (likely to retrace);
    gap  = any other gap of >= 0.3 ATR.
    """
    if gap_atr is None or abs(gap_atr) < 0.3:
        return None
    d = "up" if gap_atr > 0 else "down"
    strong = pm_rvol is not None and pm_rvol >= 2.0
    if strong and holding:
        return ("go", d)
    if abs(gap_atr) >= 1.0:
        return ("fade", d)
    return ("gap", d)
