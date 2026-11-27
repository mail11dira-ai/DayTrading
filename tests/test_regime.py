import pandas as pd

from src.backtest import Signal
from src.strategies.regime import RegimeFiltered, spy_regime


def _spy(closes):
    dates = pd.bdate_range("2026-03-02", periods=len(closes))
    return pd.DataFrame([{"symbol": "SPY", "timestamp": pd.Timestamp(d.date(), tz="America/New_York") + pd.Timedelta(hours=15, minutes=55),
                          "open": c, "high": c, "low": c, "close": c, "volume": 1} for d, c in zip(dates, closes)]), dates


def test_regime_uses_previous_close_vs_20_day_average():
    closes = [100.0] * 20 + [110.0, 90.0, 100.0]
    bars, dates = _spy(closes)
    reg = spy_regime(bars, window=20)
    # day 20 (index 20): prior close 100 vs avg 100 -> not above -> down
    assert reg[dates[20].date()] == "down"
    # day 21: prior close 110 vs avg (19*100+110)/20 = 100.5 -> up
    assert reg[dates[21].date()] == "up"
    # day 22: prior close 90 vs avg (18*100+110+90)/20 = 100 -> down
    assert reg[dates[22].date()] == "down"
    # no lookahead: the first 20 days have no regime (not enough history)
    assert dates[0].date() not in reg


def _day(date):
    ts = pd.date_range(f"{date} 10:00", periods=1, freq="5min", tz="America/New_York")
    return pd.DataFrame({"timestamp": ts, "close": [1.0]})


def test_filter_blocks_wrong_side():
    always_long = lambda day, prior: Signal("long", stop=0.9)
    always_short = lambda day, prior: Signal("short", stop=1.1)
    up, down = {pd.Timestamp("2026-03-20").date(): "up"}, {pd.Timestamp("2026-03-20").date(): "down"}
    d = _day("2026-03-20")
    assert RegimeFiltered(always_long, up)(d, d) is not None
    assert RegimeFiltered(always_long, down)(d, d) is None
    assert RegimeFiltered(always_short, down)(d, d) is not None
    assert RegimeFiltered(always_short, up)(d, d) is None
    assert RegimeFiltered(always_long, {})(d, d) is None      # no regime known -> stand aside
