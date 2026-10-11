"""Deterministic performance metrics for the intraday backtester.

Pure functions over pandas objects (numpy/pandas only, no I/O, no randomness).

Conventions
-----------
- ``equity``: pd.Series of account equity in dollars, indexed by tz-aware timestamps,
  sorted ascending. The first value is the starting equity.
- ``trades``: pd.DataFrame with at least a ``pnl`` column (net of costs, dollars).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

MARKET_TZ = "America/New_York"


def _clean_equity(equity: pd.Series) -> pd.Series:
    eq = pd.Series(equity, dtype=float).dropna()
    return eq.sort_index()


def daily_returns(equity: pd.Series) -> pd.Series:
    """Daily simple returns from an intraday equity curve.

    Takes the last equity value on each US/Eastern calendar day and computes the
    percentage change. The first day's return is measured against the very first
    equity value (the starting equity), so no day is dropped.

    Index of the result: ``datetime.date`` objects (US/Eastern trading dates).
    Raises ValueError if the index is not tz-aware (avoids silent day misbucketing).
    """
    eq = _clean_equity(equity)
    if eq.empty:
        return pd.Series(dtype=float)
    idx = pd.DatetimeIndex(eq.index)
    if idx.tz is None:
        raise ValueError("equity index must be tz-aware")
    eq.index = idx.tz_convert(MARKET_TZ)
    day_close = eq.groupby(eq.index.date).last()
    prev = day_close.shift(1)
    prev.iloc[0] = eq.iloc[0]
    rets = day_close / prev - 1.0
    rets.index.name = "date"
    return rets.astype(float)


def sharpe(daily_rets: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized Sharpe ratio, risk-free = 0, sample std (ddof=1).

    Returns 0.0 if fewer than 2 points or the std is zero.
    """
    r = pd.Series(daily_rets, dtype=float).dropna()
    if len(r) < 2:
        return 0.0
    sd = float(r.std(ddof=1))
    if sd == 0.0 or not np.isfinite(sd):
        return 0.0
    return float(r.mean() / sd * math.sqrt(periods_per_year))


def max_drawdown(equity: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a positive fraction (0.12 == -12%)."""
    eq = _clean_equity(equity)
    if eq.empty:
        return 0.0
    peak = eq.cummax()
    dd = 1.0 - eq / peak
    return float(max(dd.max(), 0.0))


def total_return(equity: pd.Series) -> float:
    """Last equity / first equity - 1. 0.0 for empty or single-point curves."""
    eq = _clean_equity(equity)
    if len(eq) < 2:
        return 0.0
    return float(eq.iloc[-1] / eq.iloc[0] - 1.0)


def _pnl(trades: pd.DataFrame | None) -> pd.Series:
    if trades is None or len(trades) == 0 or "pnl" not in trades:
        return pd.Series(dtype=float)
    return pd.Series(trades["pnl"], dtype=float).dropna()


def win_rate(trades: pd.DataFrame) -> float:
    """Fraction of trades with pnl > 0 (breakeven counts as non-win). 0.0 if no trades."""
    pnl = _pnl(trades)
    if pnl.empty:
        return 0.0
    return float((pnl > 0).sum() / len(pnl))


def profit_factor(trades: pd.DataFrame) -> float:
    """Gross profit / |gross loss|.

    inf if there are no losses but some profit; 0.0 if no trades or no profit.
    """
    pnl = _pnl(trades)
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    if pnl.empty or gross_profit == 0.0:
        return 0.0
    if gross_loss == 0.0:
        return math.inf
    return gross_profit / gross_loss


def summary(equity: pd.Series, trades: pd.DataFrame) -> dict:
    """All headline metrics in one dict."""
    pnl = _pnl(trades)
    return {
        "total_return": total_return(equity),
        "sharpe": sharpe(daily_returns(equity)),
        "max_drawdown": max_drawdown(equity),
        "win_rate": win_rate(trades),
        "profit_factor": profit_factor(trades),
        "n_trades": int(len(pnl)),
        "avg_trade_pnl": float(pnl.mean()) if len(pnl) else 0.0,
    }
