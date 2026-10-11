from datetime import time

import pytest

from src.risk import RiskLimits, entry_violations, must_flatten, position_size

L = RiskLimits()


def test_risk_per_trade():
    # $25k * 1% = $250 risk / $1 stop distance = 250 shares (notional cap 500 doesn't bind)
    assert position_size(25_000, entry=10.0, stop=9.0, limits=L) == 250


def test_position_cap():
    # risk allows 2500 shares ($0.10 stop) but 20% notional cap = $5000 / $100 = 50
    assert position_size(25_000, entry=100.0, stop=99.9, limits=L) == 50


def test_short_side_symmetric():
    assert position_size(25_000, entry=10.0, stop=11.0, limits=L) == 250


@pytest.mark.parametrize("entry,stop", [(10, 10), (0, 9), (10, 0), (-1, 5)])
def test_invalid_trades_size_zero(entry, stop):
    assert position_size(25_000, entry, stop, L) == 0


def test_zero_equity_sizes_zero():
    assert position_size(0, 10, 9, L) == 0


def test_daily_loss_halt():
    ok = entry_violations(now=time(10), equity_start_of_day=25_000,
                          realized_pnl_today=-499, open_positions=0, limits=L)
    halted = entry_violations(now=time(10), equity_start_of_day=25_000,
                              realized_pnl_today=-500, open_positions=0, limits=L)
    assert ok == []
    assert "daily loss limit reached" in halted


def test_max_open_positions():
    r = entry_violations(now=time(10), equity_start_of_day=25_000,
                         realized_pnl_today=0, open_positions=3, limits=L)
    assert r == ["max open positions reached"]


def test_eod_cutoff():
    r = entry_violations(now=time(15, 31), equity_start_of_day=25_000,
                         realized_pnl_today=0, open_positions=0, limits=L)
    assert r == ["past last entry time"]
    assert not must_flatten(time(15, 54), L)
    assert must_flatten(time(15, 55), L)


def test_limits_validated():
    with pytest.raises(ValueError):
        RiskLimits(risk_per_trade_pct=0)
    with pytest.raises(ValueError):
        RiskLimits(max_open_positions=0)
    with pytest.raises(ValueError):
        RiskLimits(last_entry_time=time(16), flatten_time=time(15, 55))
