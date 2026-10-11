from datetime import time

import pandas as pd
import pytest

from src.backtest import Config, Signal, run, split_sessions
from src.risk import RiskLimits

TZ = "America/New_York"
NO_SLIP = Config(slippage_pct=0.0)


def make_day(date, symbol="AAA", price=100.0, overrides=None):
    """78 five-minute bars 09:30..15:55 at a flat price; overrides = {bar_index: dict(open=..)}."""
    ts = pd.date_range(f"{date} 09:30", f"{date} 15:55", freq="5min", tz=TZ)
    df = pd.DataFrame({"symbol": symbol, "timestamp": ts, "open": price,
                       "high": price + 0.5, "low": price - 0.5, "close": price, "volume": 1000})
    for i, vals in (overrides or {}).items():
        for k, v in vals.items():
            df.loc[i, k] = v
    return df


def first_bar_long(stop):
    def strat(day, prior):
        return Signal("long", stop=stop) if len(day) == 1 else None
    return strat


def test_entry_next_open_and_eod_exit():
    bars = make_day("2026-03-02", overrides={1: {"open": 100.0}, 77: {"open": 110.0}})
    r = run(bars, first_bar_long(95.0), NO_SLIP)
    t = r.trades.iloc[0]
    # signal on bar 0 close -> fill at bar 1 open (09:35); qty = min(250/5, 5000/100) = 50
    assert t.entry_time == bars.timestamp[1]
    assert t.qty == 50 and t.entry_price == 100.0
    assert t.exit_reason == "eod" and t.exit_price == 110.0 and t.exit_time.time() == time(15, 55)
    assert t.pnl == pytest.approx(500.0)
    assert r.equity.iloc[-1] == pytest.approx(25_500.0)


def test_stop_hit_and_gap_through_stop():
    bars = make_day("2026-03-02", overrides={5: {"low": 94.0}})
    t = run(bars, first_bar_long(95.0), NO_SLIP).trades.iloc[0]
    assert t.exit_reason == "stop" and t.exit_price == 95.0 and t.pnl == pytest.approx(-250.0)

    gap = make_day("2026-03-02", overrides={5: {"open": 90.0, "low": 89.5}})
    t = run(gap, first_bar_long(95.0), NO_SLIP).trades.iloc[0]
    assert t.exit_price == 90.0 and t.pnl == pytest.approx(-500.0)


def test_stop_wins_when_stop_and_target_in_same_bar():
    bars = make_day("2026-03-02", overrides={5: {"low": 94.0, "high": 106.0}})
    strat = lambda day, prior: Signal("long", 95.0, target=105.0) if len(day) == 1 else None
    assert run(bars, strat, NO_SLIP).trades.iloc[0].exit_reason == "stop"


def test_short_target_and_slippage():
    bars = make_day("2026-03-02", overrides={5: {"low": 89.0}})
    strat = lambda day, prior: Signal("short", 105.0, target=90.0) if len(day) == 1 else None
    t = run(bars, strat, Config(slippage_pct=0.001)).trades.iloc[0]
    assert t.entry_price == pytest.approx(99.9)          # sell 100 * (1 - 0.001)
    assert t.exit_price == pytest.approx(90.09)          # buy 90 * (1 + 0.001)
    assert t.qty == 49                                   # min(250/5.1, 5000/99.9) -> 49
    assert t.pnl == pytest.approx((99.9 - 90.09) * 49)


def test_strategy_never_sees_future_bars():
    bars = pd.concat([make_day("2026-03-02"), make_day("2026-03-03")], ignore_index=True)
    seen = []

    def spy(day, prior):
        seen.append((day.timestamp.iloc[-1], len(day), len(prior)))
        assert (day.timestamp.dt.date == day.timestamp.iloc[-1].date()).all()
        if len(prior):
            assert prior.timestamp.iloc[-1] < day.timestamp.iloc[0]
        return None

    run(bars, spy, NO_SLIP)
    # one call per bar except the 15:55 flatten bar, each ending exactly at that bar
    expected = [ts for ts in bars.timestamp if ts.time() != time(15, 55)]
    assert [s[0] for s in seen] == expected
    assert seen[0][1:] == (1, 0) and seen[77][1:] == (1, 78)


def test_truncation_invariance():
    """Results on days 1-2 must not change when day 3 is appended (no lookahead)."""
    days = [make_day(d, overrides={10: {"high": 103.0, "close": 102.0}})
            for d in ("2026-03-02", "2026-03-03", "2026-03-04")]
    strat = lambda day, prior: Signal("long", 98.0) if day.close.iloc[-1] > 101 else None
    short = run(pd.concat(days[:2], ignore_index=True), strat, NO_SLIP).trades
    full = run(pd.concat(days, ignore_index=True), strat, NO_SLIP).trades
    pd.testing.assert_frame_equal(short, full.iloc[:len(short)])
    assert len(full) == 3


def test_risk_max_open_positions_rejects():
    bars = pd.concat([make_day("2026-03-02", "AAA"), make_day("2026-03-02", "BBB")])
    cfg = Config(slippage_pct=0.0, limits=RiskLimits(max_open_positions=1))
    r = run(bars, first_bar_long(95.0), cfg)
    assert len(r.trades) == 1
    assert r.rejected.reasons.tolist() == ["max open positions reached"]


def test_daily_loss_halt_blocks_reentry():
    # risk 1% per trade, halt at 1% -> after one full stop-out no new entry that day
    bars = make_day("2026-03-02", overrides={5: {"low": 94.0}})
    strat = lambda day, prior: Signal("long", 95.0)
    cfg = Config(slippage_pct=0.0, max_entries_per_symbol_per_day=5,
                 limits=RiskLimits(max_daily_loss_pct=0.01))
    r = run(bars, strat, cfg)
    assert len(r.trades) == 1
    assert "daily loss limit reached" in r.rejected.reasons.iloc[0]


def test_no_entries_after_last_entry_time():
    bars = make_day("2026-03-02")
    strat = lambda day, prior: Signal("long", 95.0) if day.timestamp.iloc[-1].time() == time(15, 30) else None
    r = run(bars, strat, NO_SLIP)
    assert r.trades.empty and r.rejected.reasons.tolist() == ["past last entry time"]


def test_split_sessions_by_whole_days():
    bars = pd.concat([make_day(f"2026-03-0{d}") for d in range(2, 7)])
    train, test = split_sessions(bars, 0.6)
    assert train.timestamp.dt.date.nunique() == 3 and test.timestamp.dt.date.nunique() == 2
    assert train.timestamp.max() < test.timestamp.min()
