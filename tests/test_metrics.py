import math
from datetime import date

import pandas as pd
import pytest

from src.metrics import (
    daily_returns,
    max_drawdown,
    profit_factor,
    sharpe,
    summary,
    total_return,
    win_rate,
)

NY = "America/New_York"


def _eq(values, times, tz=NY):
    return pd.Series(values, index=pd.DatetimeIndex(pd.to_datetime(times)).tz_localize(tz))


def _trades(pnls):
    n = len(pnls)
    return pd.DataFrame(
        {
            "symbol": ["AAPL"] * n,
            "side": ["long"] * n,
            "qty": [10] * n,
            "entry_price": [100.0] * n,
            "exit_price": [100.0] * n,
            "pnl": pnls,
        }
    )


# ---------- max_drawdown ----------

def test_max_drawdown_hand_example():
    # peaks: 100, 110, 110, 121. Trough 99 after peak 110 -> 1 - 99/110 = 0.10
    eq = _eq([100, 110, 99, 121], ["2024-01-02 10:00", "2024-01-02 11:00",
                                   "2024-01-02 12:00", "2024-01-02 13:00"])
    assert max_drawdown(eq) == pytest.approx(0.10)


def test_max_drawdown_monotonic_up_is_zero():
    eq = _eq([100, 101, 105], ["2024-01-02 10:00", "2024-01-02 11:00", "2024-01-02 12:00"])
    assert max_drawdown(eq) == 0.0


def test_max_drawdown_flat_and_single_point():
    assert max_drawdown(_eq([100, 100, 100], ["2024-01-02 10:00", "2024-01-02 11:00",
                                              "2024-01-02 12:00"])) == 0.0
    assert max_drawdown(_eq([100], ["2024-01-02 10:00"])) == 0.0


# ---------- total_return ----------

def test_total_return():
    # 121/100 - 1 = 0.21
    eq = _eq([100, 110, 99, 121], ["2024-01-02 10:00", "2024-01-02 11:00",
                                   "2024-01-02 12:00", "2024-01-02 13:00"])
    assert total_return(eq) == pytest.approx(0.21)


def test_total_return_single_point_and_flat():
    assert total_return(_eq([100], ["2024-01-02 10:00"])) == 0.0
    assert total_return(_eq([100, 100], ["2024-01-02 10:00", "2024-01-03 10:00"])) == 0.0


# ---------- daily_returns ----------

def test_daily_returns_first_day_vs_starting_equity():
    # Day 1 (Jan 2): starts 100, closes 102 -> 102/100 - 1 = 0.02
    # Day 2 (Jan 3): closes 99.96 -> 99.96/102 - 1 = -0.02
    eq = _eq([100, 101, 102, 103, 99.96],
             ["2024-01-02 09:31", "2024-01-02 12:00", "2024-01-02 15:59",
              "2024-01-03 10:00", "2024-01-03 15:59"])
    r = daily_returns(eq)
    assert list(r.index) == [date(2024, 1, 2), date(2024, 1, 3)]
    assert r.iloc[0] == pytest.approx(0.02)
    assert r.iloc[1] == pytest.approx(-0.02)


def test_daily_returns_buckets_by_eastern_day_from_utc():
    # 2024-01-03 01:00 UTC == 2024-01-02 20:00 ET -> belongs to Jan 2, not Jan 3.
    # 2024-01-03 15:00 UTC == 2024-01-03 10:00 ET.
    # Day Jan 2 ET: last = 110 -> 110/100 - 1 = 0.10; Day Jan 3 ET: 99/110 - 1 = -0.10
    eq = _eq([100, 110, 99],
             ["2024-01-02 15:00", "2024-01-03 01:00", "2024-01-03 15:00"], tz="UTC")
    r = daily_returns(eq)
    assert list(r.index) == [date(2024, 1, 2), date(2024, 1, 3)]
    assert r.tolist() == pytest.approx([0.10, -0.10])


def test_daily_returns_single_point_is_zero_return():
    r = daily_returns(_eq([100], ["2024-01-02 10:00"]))
    assert r.tolist() == [0.0]


def test_daily_returns_rejects_naive_index():
    eq = pd.Series([100.0, 101.0], index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    with pytest.raises(ValueError):
        daily_returns(eq)


# ---------- sharpe ----------

def test_sharpe_hand_computed():
    # r = [0.01, -0.02, 0.03]; mean = 0.02/3 = 0.0066667
    # deviations: 0.0033333, -0.0266667, 0.0233333
    # squares sum = 1.1111e-5 + 7.1111e-4 + 5.4444e-4 = 1.266667e-3
    # sample var = 1.266667e-3 / 2 = 6.333333e-4 -> sd = 0.0251661
    # sharpe = 0.0066667 / 0.0251661 * sqrt(252) = 0.264906 * 15.874508 = 4.20526
    r = pd.Series([0.01, -0.02, 0.03])
    assert sharpe(r) == pytest.approx(4.20526, rel=1e-4)


def test_sharpe_degenerate_cases():
    assert sharpe(pd.Series([0.01])) == 0.0          # < 2 points
    assert sharpe(pd.Series([], dtype=float)) == 0.0
    assert sharpe(pd.Series([0.01, 0.01, 0.01])) == 0.0  # std == 0


def test_sharpe_periods_per_year():
    r = pd.Series([0.01, -0.02, 0.03])
    assert sharpe(r, periods_per_year=1) == pytest.approx(4.20526 / math.sqrt(252), rel=1e-4)


# ---------- win_rate / profit_factor ----------

def test_win_rate_and_profit_factor_mixed():
    # pnl = [50, -20, 30, 0, -10]; wins = 2 of 5 -> 0.4 (breakeven 0 is not a win)
    # gross profit = 80, gross loss = 30 -> PF = 80/30 = 2.6667
    t = _trades([50.0, -20.0, 30.0, 0.0, -10.0])
    assert win_rate(t) == pytest.approx(0.4)
    assert profit_factor(t) == pytest.approx(80 / 30)


def test_empty_trades():
    t = _trades([])
    assert win_rate(t) == 0.0
    assert profit_factor(t) == 0.0


def test_all_winning_trades():
    t = _trades([10.0, 20.0])
    assert win_rate(t) == 1.0
    assert profit_factor(t) == math.inf


def test_all_losing_trades():
    t = _trades([-10.0, -5.0])
    assert win_rate(t) == 0.0
    assert profit_factor(t) == 0.0


# ---------- summary ----------

def test_summary_keys_and_values():
    # Equity: Jan 2 close 110 (start 100), Jan 3 close 99, Jan 4 close 121
    # daily rets: 0.10, 99/110-1 = -0.10, 121/99-1 = 0.222222
    eq = _eq([100, 110, 99, 121],
             ["2024-01-02 09:30", "2024-01-02 16:00", "2024-01-03 16:00", "2024-01-04 16:00"])
    t = _trades([10.0, -11.0, 22.0])
    s = summary(eq, t)
    assert set(s) == {"total_return", "sharpe", "max_drawdown", "win_rate",
                      "profit_factor", "n_trades", "avg_trade_pnl"}
    assert s["total_return"] == pytest.approx(0.21)
    assert s["max_drawdown"] == pytest.approx(0.10)
    assert s["win_rate"] == pytest.approx(2 / 3)
    assert s["profit_factor"] == pytest.approx(32 / 11)
    assert s["n_trades"] == 3
    assert s["avg_trade_pnl"] == pytest.approx(21 / 3)
    # mean = (0.1 - 0.1 + 0.222222)/3 = 0.0740741
    # devs: 0.0259259, -0.1740741, 0.1481481; sq sum = 0.000672154+0.030301783+0.021947874
    #     = 0.052921811; var = 0.026460905; sd = 0.1626681
    # sharpe = 0.0740741/0.1626681*15.874508 = 7.22872
    assert s["sharpe"] == pytest.approx(7.22872, rel=1e-4)


def test_summary_flat_equity_no_trades():
    eq = _eq([100, 100, 100], ["2024-01-02 10:00", "2024-01-03 10:00", "2024-01-04 10:00"])
    s = summary(eq, _trades([]))
    assert s == {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "win_rate": 0.0,
                 "profit_factor": 0.0, "n_trades": 0, "avg_trade_pnl": 0.0}
