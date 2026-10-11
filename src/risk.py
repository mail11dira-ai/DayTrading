"""Hard risk limits. Deterministic code only — every sizing/entry decision goes through here.

Never loosen these limits to get a trade or a backtest to pass.
"""
from dataclasses import dataclass
from datetime import time
import math


@dataclass(frozen=True)
class RiskLimits:
    risk_per_trade_pct: float = 0.01   # max loss to stop, as fraction of equity
    max_position_pct: float = 0.20     # max notional per position, as fraction of equity
    max_daily_loss_pct: float = 0.02   # halt new entries once day's loss reaches this
    max_open_positions: int = 3
    last_entry_time: time = time(15, 30)  # no new entries after this (US/Eastern)
    flatten_time: time = time(15, 55)     # all positions closed by this time

    def __post_init__(self):
        for name in ("risk_per_trade_pct", "max_position_pct", "max_daily_loss_pct"):
            v = getattr(self, name)
            if not 0 < v <= 1:
                raise ValueError(f"{name} must be in (0, 1], got {v}")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be >= 1")
        if self.last_entry_time >= self.flatten_time:
            raise ValueError("last_entry_time must be before flatten_time")


def position_size(equity: float, entry: float, stop: float, limits: RiskLimits) -> int:
    """Shares to buy/sell so the loss at `stop` is <= risk_per_trade_pct of equity,
    and notional is <= max_position_pct of equity. Returns 0 if the trade is invalid."""
    if equity <= 0 or entry <= 0 or stop <= 0:
        return 0
    risk_per_share = abs(entry - stop)
    if risk_per_share == 0:
        return 0
    by_risk = (equity * limits.risk_per_trade_pct) / risk_per_share
    by_notional = (equity * limits.max_position_pct) / entry
    return max(0, math.floor(min(by_risk, by_notional)))


def entry_violations(
    *,
    now: time,
    equity_start_of_day: float,
    realized_pnl_today: float,
    open_positions: int,
    limits: RiskLimits,
) -> list[str]:
    """Reasons a new entry is blocked. Empty list means the entry is allowed."""
    reasons = []
    if equity_start_of_day <= 0:
        reasons.append("non-positive equity")
    elif -realized_pnl_today >= equity_start_of_day * limits.max_daily_loss_pct:
        reasons.append("daily loss limit reached")
    if open_positions >= limits.max_open_positions:
        reasons.append("max open positions reached")
    if now > limits.last_entry_time:
        reasons.append("past last entry time")
    return reasons


def must_flatten(now: time, limits: RiskLimits) -> bool:
    """True when all positions must be closed (end of day)."""
    return now >= limits.flatten_time
