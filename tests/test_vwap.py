from datetime import time

import pandas as pd

from src.strategies.vwap import VWAPReclaim
from tests.test_backtest import make_day


def _day(closes, vols, start="2026-03-20 09:30"):
    ts = pd.date_range(start, periods=len(closes), freq="5min", tz="America/New_York")
    return pd.DataFrame({"symbol": "AAA", "timestamp": ts, "open": closes, "high": [c + 0.2 for c in closes],
                         "low": [c - 0.2 for c in closes], "close": closes, "volume": vols})


def _prior(volume=1000):
    p = pd.concat([make_day(f"2026-03-{d:02d}") for d in range(2, 12)], ignore_index=True)
    p["volume"] = volume
    return p


def test_vwap_is_cumulative_and_correct():
    d = _day([100.0, 102.0], [100, 300])
    v = VWAPReclaim().session_vwap(d)
    assert abs(v.iloc[0] - 100.0) < 1e-9                       # tp = 100 (high/low symmetric)
    assert abs(v.iloc[1] - (100 * 100 + 102 * 300) / 400) < 1e-9


def test_reclaim_long_fires_with_volume_and_stops_at_recent_low():
    # price drifts below VWAP, then crosses back above on heavy volume after 10:00
    closes = [100.0] * 8 + [99.0, 98.0, 97.0, 96.0, 97.5, 103.0]
    vols = [1000] * 13 + [12000]
    day = _day(closes, vols, start="2026-03-20 09:30")
    day["timestamp"] = day["timestamp"] + pd.Timedelta(minutes=30)   # first bar 10:00
    sig = VWAPReclaim(earliest=time(10, 0))(day, _prior())
    assert sig is not None and sig.side == "long"
    assert sig.stop == min(d.low for d in day.iloc[-6:].itertuples())
    assert sig.target > 103.0


def test_no_signal_without_volume():
    closes = [100.0] * 8 + [99.0, 98.0, 97.0, 96.0, 97.5, 103.0]
    day = _day(closes, [1000] * 14)
    day["timestamp"] = day["timestamp"] + pd.Timedelta(minutes=30)
    assert VWAPReclaim(min_rvol=1.5)(day, _prior()) is None


def test_no_signal_before_earliest_time():
    closes = [100.0] * 8 + [99.0, 98.0, 97.0, 96.0, 97.5, 103.0]
    day = _day(closes, [1000] * 13 + [12000])                   # last bar 10:35 ET
    assert VWAPReclaim(earliest=time(10, 0))(day, _prior()) is not None
    assert VWAPReclaim(earliest=time(11, 0))(day, _prior()) is None


def test_short_side_mirror():
    closes = [100.0] * 8 + [101.0, 102.0, 103.0, 104.0, 102.5, 97.0]
    day = _day(closes, [1000] * 13 + [12000])
    day["timestamp"] = day["timestamp"] + pd.Timedelta(minutes=30)
    sig = VWAPReclaim()(day, _prior())
    assert sig is not None and sig.side == "short"
    assert sig.stop == max(d.high for d in day.iloc[-6:].itertuples()) and sig.target < 97.0
    assert VWAPReclaim(allow_short=False)(day, _prior()) is None
