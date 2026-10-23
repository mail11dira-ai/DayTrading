"""Market deep dive for the MAG 7 email: SPY, QQQ and the VIX, for day trading.

All numbers are deterministic. The VIX-implied move is the standard 1-sigma estimate
(VIX / sqrt(252) per day, in %); how often SPY actually closed inside it is measured from
the downloaded history each run, so the email shows how far to trust the band.
"""
import math
from datetime import datetime

from .analyze import CT

REG_OPEN, REG_CLOSE = 8 * 60 + 30, 15 * 60 + 15  # VIX regular hours, CT (cash index updates until 15:15)


def _ct(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(CT)


def _vix_days(ds):
    """{date: [(ct_time, close, high, low)]} from VIX 5-minute bars (regular hours, interpolated bars already dropped)."""
    days = {}
    for b in ds.series("VIX", "5minute"):
        t = _ct(b["begins_at"])
        if REG_OPEN <= t.hour * 60 + t.minute < REG_CLOSE:
            days.setdefault(t.date(), []).append((t, float(b["close_value"]), float(b["high_value"]), float(b["low_value"])))
    return days


def _daily_closes(ds):
    """{date: close} for VIX from daily bars (the bar is labelled 00:00 UTC of its own date)."""
    return {datetime.fromisoformat(b["begins_at"][:10]).date(): float(b["close_value"]) for b in ds.series("VIX", "day")}


def implied_move_pct(vix):
    """1-sigma one-day move implied by the VIX, in % (VIX is an annualised % volatility)."""
    return vix / math.sqrt(252)


def band_hit_rate(spy_daily, vix_close, n=250):
    """Share of days on which SPY's close-to-close move stayed inside the prior day's VIX 1-sigma band.

    spy_daily: [(date, close)] sorted; vix_close: {date: close}. Returns (hit %, mean |move| / implied, days) or None.
    """
    hits, ratios = [], []
    for (d0, c0), (d1, c1) in zip(spy_daily, spy_daily[1:]):
        v = vix_close.get(d0)
        if not v or not c0:
            continue
        em = implied_move_pct(v)
        mv = abs(c1 / c0 - 1) * 100
        hits.append(mv <= em)
        ratios.append(mv / em)
    hits, ratios = hits[-n:], ratios[-n:]
    if len(hits) < 20:
        return None
    return 100 * sum(hits) / len(hits), sum(ratios) / len(ratios), len(hits)


def vix_analysis(ds, sday, spy=None, qqq=None):
    """VIX level, change, intraday path, 20-day / 1-year context and the SPY/QQQ implied moves for session sday."""
    days = _vix_days(ds)
    daily = _daily_closes(ds)
    today = days.get(sday, [])
    prev_days = sorted(d for d in set(days) | set(daily) if d < sday)
    pd = prev_days[-1] if prev_days else None
    prev = (days[pd][-1][1] if days.get(pd) else daily.get(pd)) if pd else None
    level = ds.indexes.get("VIX") if not today else today[-1][1]
    if level is None:
        level = prev
    if level is None:
        return None
    if prev is None:  # no history downloaded: level and regime only
        prev = level
    hist = {d: daily[d] for d in daily if d < sday}
    hist.update({d: v[-1][1] for d, v in days.items() if d < sday})  # intraday closes fill days the daily bar lags
    closes = [hist[d] for d in sorted(hist)]
    last20 = closes[-20:]
    year = closes[-252:]
    v = {
        "level": level, "prev": prev, "chg": level - prev, "chg_pct": (level / prev - 1) * 100,
        "open": today[0][1] if today else None,
        "hi": max(x[2] for x in today) if today else None, "lo": min(x[3] for x in today) if today else None,
        "chg30": (today[-1][1] - today[-7][1]) if len(today) >= 7 else None,
        "sma20": sum(last20) / len(last20) if len(last20) >= 10 else None,
        "hi20": max(last20) if last20 else None, "lo20": min(last20) if last20 else None,
        "pctile": 100 * sum(1 for c in year if c < level) / len(year) if len(year) >= 60 else None,
        "regime": "calm" if level < 15 else "normal" if level < 20 else "elevated" if level < 30 else "high",
        "em_pct": implied_move_pct(prev),  # today's band is set by the prior close, as the options market priced it
    }
    v["vs_sma20"] = (level / v["sma20"] - 1) * 100 if v["sma20"] else None
    spy_daily = [(datetime.fromisoformat(b["begins_at"][:10]).date(), float(b["close_price"])) for b in ds.series("SPY", "day")]
    v["band"] = band_hit_rate([x for x in spy_daily if x[0] < sday], hist)
    for key, r in (("spy", spy), ("qqq", qqq)):
        if not (r and r.get("ok") and r.get("levels", {}).get("PDC")):
            continue
        em = v["em_pct"]
        if key == "qqq" and spy and spy.get("atr_pct") and r.get("atr_pct"):
            em *= r["atr_pct"] / spy["atr_pct"]  # QQQ has no VIX of its own here: scale by its ATR vs SPY's
        pdc = r["levels"]["PDC"]
        used = ((r["hi"] - r["lo"]) / pdc * 100) / (2 * em) if r.get("hi") is not None and em else None
        v[key] = {"em": em, "lo": pdc * (1 - em / 100), "hi": pdc * (1 + em / 100), "pts": pdc * em / 100, "used": used,
                  "outside": (r["price"] > pdc * (1 + em / 100)) - (r["price"] < pdc * (1 - em / 100))}
    if spy and spy.get("ok") and spy.get("day_pct") is not None:
        same = (spy["day_pct"] > 0) == (v["chg"] > 0)
        v["diverge"] = None
        if same and abs(spy["day_pct"]) >= 0.2 and abs(v["chg_pct"]) >= 2:
            v["diverge"] = "up" if spy["day_pct"] > 0 else "down"
    return v
