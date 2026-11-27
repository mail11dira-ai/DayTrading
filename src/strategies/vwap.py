"""VWAP reclaim with relative volume (iter_4).

Long: the 5-minute close crosses above the session VWAP (previous bar at or below, this bar above),
after 10:00 ET, and cumulative relative volume is at least `min_rvol`.
Short: the mirror (close crosses below VWAP), if `allow_short`.
Stop = lowest low (longs) / highest high (shorts) of the last `stop_bars` bars.
Target = entry + `reward_r` x risk, so reward/risk is fixed by construction.

Uses only `day` (bars so far today) and `prior` (earlier sessions), so there is no lookahead.
"""
from dataclasses import dataclass
from datetime import time
from typing import Optional

import pandas as pd

from src.backtest import Signal


@dataclass(frozen=True)
class VWAPReclaim:
    min_rvol: float = 1.5
    rvol_lookback: int = 10
    bars_per_session: int = 78
    stop_bars: int = 6
    reward_r: float = 2.0
    earliest: time = time(10, 0)
    allow_short: bool = True

    def session_vwap(self, day: pd.DataFrame) -> pd.Series:
        tp = (day["high"] + day["low"] + day["close"]) / 3
        vol = day["volume"].astype(float)
        cum_vol = vol.cumsum()
        return (tp * vol).cumsum() / cum_vol.where(cum_vol > 0)

    def rvol(self, day: pd.DataFrame, prior: pd.DataFrame) -> Optional[float]:
        need = self.rvol_lookback * self.bars_per_session
        if len(prior) < need:
            return None
        vol = prior["volume"].to_numpy()[-need:].reshape(self.rvol_lookback, self.bars_per_session)
        base = vol[:, :len(day)].sum(axis=1).mean()
        return float(day["volume"].sum() / base) if base > 0 else None

    def __call__(self, day: pd.DataFrame, prior: pd.DataFrame) -> Optional[Signal]:
        if len(day) < max(3, self.stop_bars + 1):
            return None
        last = day.iloc[-1]
        if last.timestamp.time() < self.earliest:
            return None
        vwap = self.session_vwap(day)
        if pd.isna(vwap.iloc[-1]) or pd.isna(vwap.iloc[-2]):
            return None
        above_now, above_prev = last.close - vwap.iloc[-1], day.close.iloc[-2] - vwap.iloc[-2]
        crossed_up = above_prev <= 0 < above_now
        crossed_down = above_prev >= 0 > above_now
        if not (crossed_up or (crossed_down and self.allow_short)):
            return None
        rv = self.rvol(day, prior)
        if rv is None or rv < self.min_rvol:
            return None
        recent = day.iloc[-self.stop_bars:]
        px = float(last.close)
        if crossed_up:
            stop = float(recent["low"].min())
            risk = px - stop
            if risk <= 0:
                return None
            return Signal("long", stop=stop, target=px + self.reward_r * risk)
        stop = float(recent["high"].max())
        risk = stop - px
        if risk <= 0:
            return None
        return Signal("short", stop=stop, target=px - self.reward_r * risk)
