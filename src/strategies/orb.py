"""Opening-range breakout (ORB).

Opening range = first `range_bars` bars of the session. After the range completes, a close
above the range high goes long, a close below the range low goes short. Stop = opposite side
of the range. Optional target = entry +/- `target_r` x range height. Exit at EOD otherwise.
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

    def __call__(self, day: pd.DataFrame, prior: pd.DataFrame) -> Optional[Signal]:
        if len(day) <= self.range_bars:
            return None
        rng = day.iloc[:self.range_bars]
        hi, lo = rng["high"].max(), rng["low"].min()
        height = hi - lo
        if height <= 0:
            return None
        close = day["close"].iloc[-1]
        if close > hi:
            target = close + self.target_r * height if self.target_r else None
            return Signal("long", stop=lo, target=target)
        if close < lo and self.allow_short:
            target = close - self.target_r * height if self.target_r else None
            return Signal("short", stop=hi, target=target)
        return None
