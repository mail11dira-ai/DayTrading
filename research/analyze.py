"""Per-symbol day-trading analysis from a collect.Dataset (deterministic)."""
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import ta
from .universe import OTC

CT = ZoneInfo("America/Chicago")
OPEN, CLOSE = time(8, 30), time(15, 0)
THIN_DAILY_VOL = 100_000  # 20-day average shares/day below this = thin


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _bar(b):
    t = datetime.fromisoformat(b["begins_at"].replace("Z", "+00:00")).astimezone(CT)
    sess = b.get("session")
    if sess not in ("pre", "reg", "post"):
        sess = "reg" if OPEN <= t.time() < CLOSE else ("pre" if t.time() < OPEN else "post")
    return {"t": t, "d": t.date(), "o": _f(b["open_price"]), "h": _f(b["high_price"]),
            "l": _f(b["low_price"]), "c": _f(b["close_price"]), "v": float(b.get("volume") or 0),
            "s": sess}


def _daily(b):
    return {"d": date.fromisoformat(b["begins_at"][:10]), "o": _f(b["open_price"]),
            "h": _f(b["high_price"]), "l": _f(b["low_price"]), "c": _f(b["close_price"]),
            "v": float(b.get("volume") or 0)}


def detect_mode(ds, now, probe=("SPY", "QQQ")):
    """Returns (mode, session_date): 'intraday' | 'premarket' | 'closed'."""
    today = now.date()
    reg_dates, pre_today = set(), False
    for sym in probe:
        for b in map(_bar, ds.series(sym, "5minute")):
            if b["s"] == "reg":
                reg_dates.add(b["d"])
            elif b["s"] == "pre" and b["d"] == today:
                pre_today = True
    if today in reg_dates:
        return ("intraday" if now.time() < CLOSE else "closed"), today
    if pre_today and now.time() < OPEN:
        return "premarket", today
    last = max(reg_dates) if reg_dates else today
    return "closed", last


def _quote_price(q, mode):
    """Latest price from a quote record (most recent of regular / extended)."""
    if not q:
        return None
    qq = q.get("quote", {})
    cand = []
    for p, t in (("last_trade_price", "venue_last_trade_time"),
                 ("last_non_reg_trade_price", "venue_last_non_reg_trade_time")):
        if qq.get(p) and qq.get(t):
            cand.append((qq[t], _f(qq[p])))
    return max(cand)[1] if cand else None


def analyze(ds, sym, mode, sday, now):
    """Full technical analysis for one symbol; returns a dict (values may be None)."""
    r = {"sym": sym, "ok": False, "thin": sym in OTC}
    five = [_bar(b) for b in ds.series(sym, "5minute")]
    daily_all = [_daily(b) for b in ds.series(sym, "day")]
    reg = [b for b in five if b["s"] == "reg"]
    today_reg = [b for b in reg if b["d"] == sday] if mode != "premarket" else []
    pre_today = [b for b in five if b["s"] == "pre" and b["d"] == sday]
    prior_dates = sorted({b["d"] for b in reg if b["d"] < sday})[-10:]
    prior = {d: [b for b in reg if b["d"] == d] for d in prior_dates}
    daily = [b for b in daily_all if b["d"] < sday and b["c"]]
    q = ds.quotes.get(sym)

    # --- price and reference closes
    if mode == "intraday":
        price = _quote_price(q, mode) or (today_reg[-1]["c"] if today_reg else None)
    elif mode == "premarket":
        price = (pre_today[-1]["c"] if pre_today else None) or _quote_price(q, mode)
    else:
        price = today_reg[-1]["c"] if today_reg else None
    if price is None and q:
        price = _f(q["quote"].get("last_trade_price"))
    if daily:
        prev = daily[-1]
    elif prior_dates:
        pb = prior[prior_dates[-1]]
        prev = {"h": max(b["h"] for b in pb), "l": min(b["l"] for b in pb), "c": pb[-1]["c"]}
    else:
        prev = None
    pdc = prev["c"] if prev else (_f(q["quote"].get("adjusted_previous_close")) if q else None)
    if price is None or pdc is None:
        return r
    r.update(ok=True, price=price, pdc=pdc, day_pct=(price / pdc - 1) * 100)

    # --- daily indicators (completed bars + today's price as the last close)
    dc = [b["c"] for b in daily] + [price]
    r["d_ema9"] = ta.ema_series(dc, 9)[-1]
    r["d_ema21"] = ta.ema_series(dc, 21)[-1]
    r["sma20"], r["sma50"], r["sma200"] = ta.sma(dc, 20), ta.sma(dc, 50), ta.sma(dc, 200)
    r["stack"] = ta.ma_stack(price, r["d_ema9"], r["d_ema21"], r["sma50"])
    r["cross"] = ta.last_cross(ta.sma_series(dc, 50), ta.sma_series(dc, 200), 10)
    r["rsi_d"] = ta.rsi_series(dc, 14)[-1]
    atrs = ta.atr_series([b["h"] for b in daily], [b["l"] for b in daily], [b["c"] for b in daily], 14)
    atr = atrs[-1] if atrs else None
    r["atr"] = atr
    r["atr_pct"] = atr / price * 100 if atr else None
    avg20v = ta.sma([b["v"] for b in daily], 20)
    if avg20v is not None and avg20v < THIN_DAILY_VOL:
        r["thin"] = True

    # --- today's session
    if today_reg:
        r["open"] = today_reg[0]["o"]
        r["hi"] = max(b["h"] for b in today_reg)
        r["lo"] = min(b["l"] for b in today_reg)
    else:
        r["open"] = price if mode == "premarket" else None
        r["hi"] = r["lo"] = None
    r["range_used"] = (r["hi"] - r["lo"]) / atr if (atr and r["hi"] is not None) else None
    if atr and r["range_used"] is not None:
        rem = max(0.0, atr - (r["hi"] - r["lo"]))
        r["exp_lo"], r["exp_hi"] = price - rem, price + rem
    else:
        r["exp_lo"] = r["exp_hi"] = None
    r["gap_pct"] = (r["open"] / pdc - 1) * 100 if r["open"] else None
    if r["gap_pct"] is not None and r["lo"] is not None:
        r["gap_filled"] = r["lo"] <= pdc if r["gap_pct"] > 0 else r["hi"] >= pdc
    else:
        r["gap_filled"] = None

    # --- volume
    r["rvol"] = r["vol_trend"] = r["ud"] = None
    r["spikes"] = []
    if today_reg and prior:
        last_t = today_reg[-1]["t"].time()
        cum = sum(b["v"] for b in today_reg)
        pcs = [sum(b["v"] for b in bars if b["t"].time() <= last_t) for bars in prior.values()]
        pavg = sum(pcs) / len(pcs) if pcs else 0
        r["rvol"] = cum / pavg if pavg else None
        slot = {}
        for bars in prior.values():
            for b in bars:
                slot.setdefault(b["t"].time(), []).append(b["v"])
        for b in today_reg:
            vs = slot.get(b["t"].time())
            if vs:
                a = sum(vs) / len(vs)
                if a > 0 and b["v"] > 3 * a:
                    r["spikes"].append((b["t"].strftime("%H:%M"), b["v"] / a, "up" if b["c"] >= b["o"] else "dn"))
    if today_reg:
        avgv = sum(b["v"] for b in today_reg) / len(today_reg)
        last3 = today_reg[-3:]
        if avgv > 0:
            r["vol_trend"] = sum(b["v"] for b in last3) / len(last3) / avgv
        up = sum(b["v"] for b in today_reg if b["c"] > b["o"])
        dn = sum(b["v"] for b in today_reg if b["c"] < b["o"])
        r["ud"] = up / dn if dn else (None if up == 0 else 99.0)

    # --- VWAP
    r["vwap"] = r["vwap_sd"] = r["vwap_slope"] = r["vwap_event"] = None
    if today_reg:
        vw, sd = ta.vwap_series(today_reg)
        if vw[-1] is not None:
            r["vwap"], r["vwap_sd"] = vw[-1], sd[-1]
            if len(vw) >= 7 and vw[-7] is not None:
                ch = (vw[-1] - vw[-7]) / price * 100
                r["vwap_slope"] = "up" if ch > 0.05 else "down" if ch < -0.05 else "flat"
            ev, i = ta.vwap_event([b["c"] for b in today_reg], vw)
            if ev:
                r["vwap_event"] = (ev, today_reg[i]["t"].strftime("%H:%M"))
    r["vs_vwap"] = (price / r["vwap"] - 1) * 100 if r["vwap"] else None
    r["vs_vwap_atr"] = (price - r["vwap"]) / atr if (r["vwap"] and atr) else None

    # --- 5-minute EMA / RSI / ATR on the continuous regular series
    series5 = [b for d in prior_dates for b in prior[d]] + today_reg
    if mode == "premarket":
        series5 += pre_today
    c5 = [b["c"] for b in series5]
    e9, e21 = ta.ema_series(c5, 9), ta.ema_series(c5, 21)
    r["ema9_5"], r["ema21_5"] = e9[-1] if e9 else None, e21[-1] if e21 else None
    r["ema_bull"] = None if None in (r["ema9_5"], r["ema21_5"]) else r["ema9_5"] > r["ema21_5"]
    r["ema_cross"] = None
    if len(c5) > 7 and None not in (e9[-7], e21[-7]):
        was = e9[-7] > e21[-7]
        if was != r["ema_bull"]:
            r["ema_cross"] = "bull" if r["ema_bull"] else "bear"
    rs5 = ta.rsi_series(c5, 14)
    r["rsi_5"] = rs5[-1] if rs5 else None
    a5 = ta.atr_series([b["h"] for b in series5], [b["l"] for b in series5], c5, 14)
    r["atr_5"] = a5[-1] if a5 else None
    r["div"] = ta.divergence([b["h"] for b in series5], [b["l"] for b in series5], rs5) if mode != "premarket" else None
    h5, l5 = [b["h"] for b in series5], [b["l"] for b in series5]
    _, msig, mh = ta.macd_series(c5)
    r["macd_hist"] = mh[-1] if mh else None
    r["macd_prev"] = mh[-2] if len(mh) > 1 else None
    r["macd_state"] = None
    if r["macd_hist"] is not None and r["macd_prev"] is not None:
        side = "bullish" if r["macd_hist"] > 0 else "bearish"
        grow = abs(r["macd_hist"]) >= abs(r["macd_prev"])
        r["macd_state"] = f"{side}, {'expanding' if grow else 'fading'}"
    r["macd_cross"] = None
    if len(mh) > 7 and None not in (mh[-7], mh[-1]) and (mh[-7] > 0) != (mh[-1] > 0):
        r["macd_cross"] = "bull" if mh[-1] > 0 else "bear"
    adx, pdi, mdi = ta.adx_series(h5, l5, c5, 14)
    r["adx"], r["pdi"], r["mdi"] = (adx[-1], pdi[-1], mdi[-1]) if adx else (None, None, None)
    r["sqz"] = ta.squeeze(h5, l5, c5)

    # --- levels
    lv = {}
    if prev:
        lv.update(PDH=prev["h"], PDL=prev["l"], PDC=prev["c"])
        lv.update(ta.floor_pivots(prev["h"], prev["l"], prev["c"]))
    if pre_today:
        lv["PMH"], lv["PML"] = max(b["h"] for b in pre_today), min(b["l"] for b in pre_today)
    if len(today_reg) >= 3:
        lv["ORH"], lv["ORL"] = max(b["h"] for b in today_reg[:3]), min(b["l"] for b in today_reg[:3])
    if daily:
        wk0 = sday - timedelta(days=sday.weekday())
        prev_wk = [b for b in daily if b["d"] < wk0]
        if prev_wk:
            mon = prev_wk[-1]["d"] - timedelta(days=prev_wk[-1]["d"].weekday())
            wk = [b for b in prev_wk if b["d"] >= mon]
            lv["PWH"], lv["PWL"] = max(b["h"] for b in wk), min(b["l"] for b in wk)
    if prior_dates and atr:
        vp = ta.volume_profile(prior[prior_dates[-1]], atr / 20)
        if vp:
            lv.update(vp)
    if len(daily) >= 20:
        lv["20dH"], lv["20dL"] = max(b["h"] for b in daily[-20:]), min(b["l"] for b in daily[-20:])
    if daily:
        hs = [b["h"] for b in daily[-252:]] + ([r["hi"]] if r["hi"] else [])
        ls = [b["l"] for b in daily[-252:]] + ([r["lo"]] if r["lo"] else [])
        lv["52wH"], lv["52wL"] = max(hs), min(ls)
    r["levels"] = lv
    r["pattern"] = ta.daily_pattern([b["h"] for b in daily], [b["l"] for b in daily])
    pts = [(v, k) for k, v in lv.items() if v]
    if atr:
        pts += ta.round_levels(price, atr)
    if r["vwap"] and not r["thin"]:
        pts.append((r["vwap"], "VWAP"))
        if r["vwap_sd"]:
            pts += [(r["vwap"] + 2 * r["vwap_sd"], "VWAP+2s"), (r["vwap"] - 2 * r["vwap_sd"], "VWAP-2s")]
    zones = ta.merge_zones(pts, atr, price)
    r["sup"], r["res"] = ta.nearest(zones, price)
    r["watch"] = ta.watch_levels(price, atr, zones)

    # --- structure and breaks
    r["struct"] = ta.structure([b["h"] for b in today_reg], [b["l"] for b in today_reg]) if today_reg else None
    br = []
    for name, up in (("ORH", True), ("ORL", False), ("PDH", True), ("PDL", False), ("PMH", True), ("PML", False)):
        v = lv.get(name)
        if v and ((up and price > v) or (not up and price < v)):
            br.append(f"{name} {'up' if up else 'dn'}")
    r["breaks"] = br

    # --- bias
    side = None if r["vwap"] is None else (price > r["vwap"]) - (price < r["vwap"])
    r["bias"], r["bias_label"], r["bias_comp"] = ta.bias_score(
        side, r["ema_bull"], r["stack"], r["rsi_5"], r["rvol"], r["ud"], r["struct"],
        vwap_ok=not r["thin"])
    r["conf"] = ta.confirmations(r["bias"], r["macd_hist"], r["macd_prev"], r["adx"], r["pdi"], r["mdi"])
    side_key = "bull" if r["bias"] > 0 else "bear" if r["bias"] < 0 else None
    r["setup"] = r["watch"].get(side_key) if side_key else None
    return r


def earnings_within(ds, syms, start, days=14):
    end = start + timedelta(days=days)
    out = {}
    for e in ds.earnings:
        s = e.get("symbol")
        d = (e.get("report") or {}).get("date")
        if s in syms and d:
            dd = date.fromisoformat(d)
            if start <= dd <= end:
                out[s] = (dd, (e["report"].get("timing") or ""))
    return out


def now_ct(arg=None):
    if arg:
        dt = datetime.fromisoformat(arg)
        return dt.astimezone(CT) if dt.tzinfo else dt.replace(tzinfo=CT)
    return datetime.now(timezone.utc).astimezone(CT)
