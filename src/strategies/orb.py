"""Opening-range breakout (ORB).

Opening range = first `range_bars` bars of the session. After the range completes, a close
above the range high goes long, a close below the range low goes short. Stop = opposite side
of the range. Optional target = entry +/- `target_r` x range height. Exit at EOD otherwise.

Optional relative-volume filter (`min_rvol`): today's cumulative volume up to the current bar
divided by the average cumulative volume at the same bar over the previous `rvol_lookback`
sessions. Uses only `prior` and `day`, so no lookahead.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.backtest import Signal


@dataclass(frozen=True)
class ORB:
    range_bars: int = 6              # 6 x 5 min = 30-minute opening range
    target_r: Optional[float] = None
    allow_short: bool = True
    min_rvol: Optional[float] = None
    rvol_lookback: int = 10
    bars_per_session: int = 78

    def rvol(self, day: pd.DataFrame, prior: pd.DataFrame) -> Optional[float]:
        need = self.rvol_lookback * self.bars_per_session
        if len(prior) < need:
            return None
        vol = prior["volume"].to_numpy()[-need:].reshape(self.rvol_lookback, self.bars_per_session)
        base = vol[:, :len(day)].sum(axis=1).mean()
        return float(day["volume"].sum() / base) if base > 0 else None

    def __call__(self, day: pd.DataFrame, prior: pd.DataFrame) -> Optional[Signal]:
        if len(day) <= self.range_bars:
            return None
        rng = day.iloc[:self.range_bars]
        hi, lo = rng["high"].max(), rng["low"].min()
        height = hi - lo
        if height <= 0:
            return None
        close = day["close"].iloc[-1]
        if not (close > hi or (close < lo and self.allow_short)):
            return None
        if self.min_rvol is not None:
            rv = self.rvol(day, prior)
            if rv is None or rv < self.min_rvol:
                return None
        if close > hi:
            target = close + self.target_r * height if self.target_r else None
            return Signal("long", stop=lo, target=target)
        if close < lo and self.allow_short:
            target = close - self.target_r * height if self.target_r else None
            return Signal("short", stop=hi, target=target)
        return None
