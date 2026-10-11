import pandas as pd

from src.strategies.orb import ORB
from tests.test_backtest import make_day


def _hist(today_vol, prior_vol, sessions=10):
    prior = pd.concat([make_day(f"2026-03-{d:02d}") for d in range(2, 2 + sessions)], ignore_index=True)
    prior["volume"] = prior_vol
    day = make_day("2026-03-20").iloc[:8].copy()
    day["volume"] = today_vol
    day.loc[7, "close"] = 101.0                      # breakout above range high 100.5
    return day, prior


def test_breakout_long_with_stop_at_range_low():
    day, prior = _hist(1000, 1000)
    sig = ORB()(day, prior)
    assert sig.side == "long" and sig.stop == 99.5


def test_rvol_filter():
    day, prior = _hist(2000, 1000)                   # rvol = 2.0
    assert ORB(min_rvol=1.5)(day, prior) is not None
    assert ORB(min_rvol=2.5)(day, prior) is None


def test_rvol_needs_enough_history():
    day, prior = _hist(2000, 1000, sessions=5)
    assert ORB(min_rvol=1.0)(day, prior) is None
    assert ORB()(day, prior) is not None             # filter off -> history not required
