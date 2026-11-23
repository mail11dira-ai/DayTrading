"""Node X4: support/resistance and entry/exit plan from Robinhood bars. Code only.

Input: saved Robinhood MCP `get_equity_historicals` responses (5-minute, bounds="extended",
covering ~10 prior sessions plus today's pre-market). Bars are classified by ET clock time.

Levels: prior-session high/low/close, classic floor pivots (P, R1, R2, S1, S2), pre-market
high/low (PMH/PML), ATR(10) from daily true ranges, gap %, pre-market relative volume.
"""
from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

import pandas as pd

from src.risk import RiskLimits, position_size
from xers.config import ET

REG_OPEN, REG_CLOSE, PRE_OPEN = time(9, 30), time(16, 0), time(4, 0)


def load_bars(paths) -> pd.DataFrame:
    rows = []
    for p in paths:
        payload = json.loads(Path(p).read_text())
        for res in payload["data"]["results"]:
            for b in res["bars"]:
                if b.get("interpolated"):
                    continue
                rows.append({"symbol": res["symbol"], "timestamp": b["begins_at"],
                             "open": float(b["open_price"]), "high": float(b["high_price"]),
                             "low": float(b["low_price"]), "close": float(b["close_price"]),
                             "volume": int(b["volume"])})
    df = pd.DataFrame(rows, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(ET)
    return df.drop_duplicates(["symbol", "timestamp"]).sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def compute_levels(bars: pd.DataFrame, trade_date: date, atr_days: int = 10) -> dict | None:
    """Levels for one symbol's bars. None if there is no prior regular session."""
    b = bars.copy()
    b["date"], b["clock"] = b["timestamp"].dt.date, b["timestamp"].dt.time
    reg = b[(b["clock"] >= REG_OPEN) & (b["clock"] < REG_CLOSE) & (b["date"] < trade_date)]
    if reg.empty:
        return None
    daily = reg.groupby("date").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    prev = daily.iloc[-1]
    H, L, C = float(prev.high), float(prev.low), float(prev.close)
    tr = pd.concat([daily.high - daily.low, (daily.high - daily.close.shift()).abs(),
                    (daily.low - daily.close.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.tail(atr_days).mean())

    P = (H + L + C) / 3
    lv = {"prev_date": str(daily.index[-1]), "prev_high": H, "prev_low": L, "prev_close": C,
          "P": P, "R1": 2 * P - L, "S1": 2 * P - H, "R2": P + (H - L), "S2": P - (H - L), "atr": atr}

    pre = b[(b["date"] == trade_date) & (b["clock"] >= PRE_OPEN) & (b["clock"] < REG_OPEN)]
    if pre.empty:
        lv.update(PMH=None, PML=None, last=C, gap_pct=0.0, pm_volume=0, pm_rvol=None)
    else:
        last_clock = pre["clock"].iloc[-1]
        prior_pre = b[(b["date"] < trade_date) & (b["clock"] >= PRE_OPEN) & (b["clock"] <= last_clock)]
        base = prior_pre.groupby("date")["volume"].sum().mean() if not prior_pre.empty else 0
        vol = int(pre["volume"].sum())
        last = float(pre["close"].iloc[-1])
        lv.update(PMH=float(pre["high"].max()), PML=float(pre["low"].min()), last=last,
                  gap_pct=(last - C) / C, pm_volume=vol, pm_rvol=(vol / base) if base else None)
    return lv


def plan(lv: dict, side: str, equity: float = 25_000.0, limits: RiskLimits | None = None) -> dict:
    """Mechanical entry/stop/targets. side = 'bullish' (long) or 'bearish' (short)."""
    atr = lv["atr"]
    merged: dict[float, str] = {}                  # levels at the same price share one name
    for k in ("PMH", "PML", "prev_high", "prev_low", "prev_close", "P", "R1", "R2", "S1", "S2"):
        if lv.get(k) is not None:
            px = round(lv[k], 2)
            merged[px] = f"{merged[px]}/{k}" if px in merged else k
    named = {name: px for px, name in merged.items()}
    if side == "bullish":
        entry_name = next(n for n in named if n.split("/")[0] == ("PMH" if lv["PMH"] is not None else "prev_high"))
        entry = named[entry_name]
        below = {k: v for k, v in named.items() if v <= entry - 0.15 * atr}
        stop_name, stop = max(below.items(), key=lambda kv: kv[1]) if below else ("0.5 ATR", entry - 0.5 * atr)
        if entry - stop > atr:
            stop_name, stop = "1 ATR", entry - atr
        above = sorted((v, k) for k, v in named.items() if v >= entry + 0.25 * atr)
        t1 = above[0] if above else (entry + atr, "1 ATR")
        t2 = above[1] if len(above) > 1 else (max(entry + 2 * atr, t1[0] + 0.5 * atr), "2 ATR")
    else:
        entry_name = next(n for n in named if n.split("/")[0] == ("PML" if lv["PML"] is not None else "prev_low"))
        entry = named[entry_name]
        above = {k: v for k, v in named.items() if v >= entry + 0.15 * atr}
        stop_name, stop = min(above.items(), key=lambda kv: kv[1]) if above else ("0.5 ATR", entry + 0.5 * atr)
        if stop - entry > atr:
            stop_name, stop = "1 ATR", entry + atr
        below = sorted(((v, k) for k, v in named.items() if v <= entry - 0.25 * atr), reverse=True)
        t1 = below[0] if below else (entry - atr, "1 ATR")
        t2 = below[1] if len(below) > 1 else (min(entry - 2 * atr, t1[0] - 0.5 * atr), "2 ATR")

    risk = abs(entry - stop)
    rr = abs(t1[0] - entry) / risk if risk else 0.0
    levels_sorted = sorted(named.items(), key=lambda kv: kv[1])
    return {
        "side": "long" if side == "bullish" else "short",
        "entry": entry, "entry_level": entry_name,
        "stop": stop, "stop_level": stop_name,
        "t1": t1[0], "t1_level": t1[1], "t2": t2[0], "t2_level": t2[1],
        "rr_t1": rr,
        "shares": position_size(equity, entry, stop, limits or RiskLimits()),
        "supports": [(k, v) for k, v in levels_sorted if v < lv["last"]][::-1][:3],
        "resistances": [(k, v) for k, v in levels_sorted if v > lv["last"]][:3],
    }
