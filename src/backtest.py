"""Node N2: event-driven intraday backtester.

Lookahead protection is structural:
- A strategy sees only bars up to and including the current bar (`day` = today's bars so far,
  `prior` = all earlier sessions for that symbol).
- A signal produced on bar t's close is filled at bar t+1's open.
- Stops/targets are checked intrabar against high/low; if both could trigger in one bar,
  the stop is assumed to hit first (conservative). Gaps through a stop fill at the open.
- Every entry is sized and permitted by `src/risk.py`; nothing here overrides it.

Per-bar order of events: EOD flatten (open) -> pending entry fills (open) ->
stops/targets (intrabar) -> mark to market (close) -> new signals (close).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from src.risk import RiskLimits, entry_violations, must_flatten, position_size


@dataclass(frozen=True)
class Signal:
    side: str                        # 'long' or 'short'
    stop: float
    target: Optional[float] = None

    def __post_init__(self):
        if self.side not in ("long", "short"):
            raise ValueError(f"side must be 'long' or 'short', got {self.side!r}")


Strategy = Callable[[pd.DataFrame, pd.DataFrame], Optional[Signal]]


@dataclass
class Config:
    starting_equity: float = 25_000.0
    slippage_pct: float = 0.0002     # per side, applied against us
    commission_per_share: float = 0.0
    max_entries_per_symbol_per_day: int = 1
    limits: RiskLimits = field(default_factory=RiskLimits)


@dataclass
class _Position:
    symbol: str
    side: str
    qty: int
    entry_time: pd.Timestamp
    entry_price: float
    stop: float
    target: Optional[float]


@dataclass
class Result:
    trades: pd.DataFrame
    equity: pd.Series
    rejected: pd.DataFrame           # signals blocked by risk rules, with reasons


TRADE_COLUMNS = ["symbol", "entry_time", "exit_time", "side", "qty",
                 "entry_price", "exit_price", "pnl", "exit_reason"]


def _fill(price: float, buying: bool, slip: float) -> float:
    return price * (1 + slip) if buying else price * (1 - slip)


def run(bars: pd.DataFrame, strategy: Strategy, config: Config | None = None) -> Result:
    """Backtest `strategy` over `bars` (columns: symbol, timestamp, open, high, low, close, volume;
    timestamps tz-aware US/Eastern, regular hours)."""
    cfg = config or Config()
    lim = cfg.limits
    bars = bars.sort_values(["timestamp", "symbol"]).reset_index(drop=True)

    # Per-symbol frames with a session column, for O(1) history slicing.
    per_sym: dict[str, pd.DataFrame] = {}
    for sym, g in bars.groupby("symbol"):
        g = g.reset_index(drop=True)
        g["session"] = g["timestamp"].dt.date
        per_sym[sym] = g
    cursor = {s: -1 for s in per_sym}                       # index of current bar per symbol
    day_start = {s: 0 for s in per_sym}

    cash = cfg.starting_equity
    positions: dict[str, _Position] = {}
    pending: dict[str, Signal] = {}
    trades, rejected, equity_pts = [], [], []
    session = None
    realized_today = 0.0
    equity_sod = cfg.starting_equity
    entries_today: dict[str, int] = {}
    last_close: dict[str, float] = {}

    def close_position(pos: _Position, raw_price: float, ts, reason: str):
        nonlocal cash, realized_today
        buying = pos.side == "short"
        px = _fill(raw_price, buying, cfg.slippage_pct)
        sign = 1 if pos.side == "long" else -1
        pnl = sign * (px - pos.entry_price) * pos.qty - cfg.commission_per_share * pos.qty
        cash += pnl
        realized_today += pnl
        trades.append([pos.symbol, pos.entry_time, ts, pos.side, pos.qty,
                       pos.entry_price, px, pnl, reason])
        del positions[pos.symbol]

    for ts, step in bars.groupby("timestamp", sort=True):
        now = ts.time()
        if ts.date() != session:
            session = ts.date()
            realized_today = 0.0
            entries_today = {}
            pending.clear()                                   # signals never carry overnight
            mtm = sum((last_close[p.symbol] - p.entry_price) * p.qty * (1 if p.side == "long" else -1)
                      for p in positions.values())
            equity_sod = cash + mtm
            for s, g in per_sym.items():
                nxt = cursor[s] + 1
                if nxt < len(g) and g.at[nxt, "session"] == session:
                    day_start[s] = nxt

        rows = {r.symbol: r for r in step.itertuples(index=False)}
        for s in rows:
            cursor[s] += 1

        # 1) end-of-day flatten at the open of the flatten bar
        if must_flatten(now, lim):
            for pos in list(positions.values()):
                if pos.symbol in rows:
                    close_position(pos, rows[pos.symbol].open, ts, "eod")
            pending.clear()

        # 2) fill pending entries at this bar's open, through the risk module
        for sym, sig in list(pending.items()):
            del pending[sym]
            if sym not in rows or sym in positions:
                continue
            bar = rows[sym]
            reasons = entry_violations(now=now, equity_start_of_day=equity_sod,
                                       realized_pnl_today=realized_today,
                                       open_positions=len(positions), limits=lim)
            buying = sig.side == "long"
            px = _fill(bar.open, buying, cfg.slippage_pct)
            if (buying and sig.stop >= px) or (not buying and sig.stop <= px):
                reasons.append("stop on wrong side of fill")
            qty = 0 if reasons else position_size(cash, px, sig.stop, lim)
            if not reasons and qty == 0:
                reasons.append("position size zero")
            if reasons:
                rejected.append([sym, ts, sig.side, "; ".join(reasons)])
                continue
            positions[sym] = _Position(sym, sig.side, qty, ts, px, sig.stop, sig.target)
            entries_today[sym] = entries_today.get(sym, 0) + 1

        # 3) stops and targets, intrabar (stop wins ties)
        for pos in list(positions.values()):
            bar = rows.get(pos.symbol)
            if bar is None:
                continue
            if pos.side == "long":
                if bar.low <= pos.stop:
                    close_position(pos, min(bar.open, pos.stop), ts, "stop")
                elif pos.target is not None and bar.high >= pos.target:
                    close_position(pos, max(bar.open, pos.target), ts, "target")
            else:
                if bar.high >= pos.stop:
                    close_position(pos, max(bar.open, pos.stop), ts, "stop")
                elif pos.target is not None and bar.low <= pos.target:
                    close_position(pos, min(bar.open, pos.target), ts, "target")

        # 4) mark to market at close
        for s, r in rows.items():
            last_close[s] = r.close
        mtm = sum((last_close[p.symbol] - p.entry_price) * p.qty * (1 if p.side == "long" else -1)
                  for p in positions.values())
        equity_pts.append((ts, cash + mtm))

        # 5) new signals on this bar's close, for the next bar
        if must_flatten(now, lim):
            continue
        for sym in rows:
            if sym in positions or sym in pending:
                continue
            if entries_today.get(sym, 0) >= cfg.max_entries_per_symbol_per_day:
                continue
            g, i, d0 = per_sym[sym], cursor[sym], day_start[sym]
            sig = strategy(g.iloc[d0:i + 1], g.iloc[:d0])
            if sig is not None:
                pending[sym] = sig

    # Anything still open at the very end (data ends mid-session) closes at last close.
    for pos in list(positions.values()):
        close_position(pos, last_close[pos.symbol], equity_pts[-1][0], "end_of_data")
    if equity_pts:
        equity_pts[-1] = (equity_pts[-1][0], cash)

    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    equity = pd.Series([e for _, e in equity_pts], index=pd.DatetimeIndex([t for t, _ in equity_pts]),
                       name="equity", dtype=float)
    rejected_df = pd.DataFrame(rejected, columns=["symbol", "time", "side", "reasons"])
    return Result(trades_df, equity, rejected_df)


def split_sessions(bars: pd.DataFrame, train_frac: float = 0.7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by whole sessions: first `train_frac` of sessions = train, rest = test."""
    sessions = sorted(bars["timestamp"].dt.date.unique())
    cut = sessions[int(len(sessions) * train_frac)]
    is_train = bars["timestamp"].dt.date < cut
    return bars[is_train].copy(), bars[~is_train].copy()
