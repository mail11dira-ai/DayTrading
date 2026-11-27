"""Market-regime filter (iter_5): only trade with the broad market.

SPY's daily close is compared with its own 20-day average, using only sessions BEFORE the trade
day (the prior day's close vs its average), so there is no lookahead.
Longs are allowed only in an uptrend (SPY above its average), shorts only in a downtrend.
Wraps any strategy with the signature strategy(day, prior) -> Signal | None.
"""
from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

from src.backtest import Signal


def spy_regime(bars: pd.DataFrame, window: int = 20, symbol: str = "SPY") -> dict:
    """Map each trading date to 'up' or 'down' using SPY's close vs its `window`-day average,
    evaluated at the PREVIOUS session's close. Dates without enough history are absent."""
    spy = bars[bars["symbol"] == symbol]
    daily = spy.groupby(spy["timestamp"].dt.date)["close"].last().sort_index()
    avg = daily.rolling(window).mean()
    regime = {}
    dates = list(daily.index)
    for i in range(1, len(dates)):
        prev_close, prev_avg = daily.iloc[i - 1], avg.iloc[i - 1]
        if pd.isna(prev_avg):
            continue
        regime[dates[i]] = "up" if prev_close > prev_avg else "down"
    return regime


class RegimeFiltered:
    def __init__(self, base: Callable[[pd.DataFrame, pd.DataFrame], Optional[Signal]], regime: dict):
        self.base = base
        self.regime = regime

    def __call__(self, day: pd.DataFrame, prior: pd.DataFrame) -> Optional[Signal]:
        sig = self.base(day, prior)
        if sig is None:
            return None
        r = self.regime.get(day.timestamp.iloc[-1].date())
        if r is None:
            return None                       # not enough history for a regime: stand aside
        if sig.side == "long" and r != "up":
            return None
        if sig.side == "short" and r != "down":
            return None
        return sig
