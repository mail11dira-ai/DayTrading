import json

import pandas as pd

from src.data import TZ, parse_raw, validate


def _bar(ts, px, interpolated=False):
    b = {"begins_at": ts, "open_price": str(px), "high_price": str(px + 1),
         "low_price": str(px - 1), "close_price": str(px), "volume": 100, "session": "reg"}
    if interpolated:
        b["interpolated"] = True
    return b


def _write(tmp_path, bars, interval="5minute"):
    p = tmp_path / "raw.txt"
    p.write_text(json.dumps({"data": {"results": [
        {"symbol": "SPY", "interval": interval, "bars": bars}]}, "guide": ""}))
    return p


def test_parse_drops_interpolated_and_converts_tz(tmp_path):
    p = _write(tmp_path, [_bar("2026-03-02T14:30:00Z", 100),
                          _bar("2026-03-02T14:35:00Z", 100, interpolated=True)])
    df = parse_raw(p)
    assert len(df) == 1
    assert str(df["timestamp"].dt.tz) == TZ
    assert df["timestamp"].iloc[0].hour == 9 and df["timestamp"].iloc[0].minute == 30


def test_parse_ignores_other_intervals(tmp_path):
    p = _write(tmp_path, [_bar("2026-03-02T14:30:00Z", 100)], interval="30minute")
    assert parse_raw(p).empty


def _frame(rows):
    df = pd.DataFrame(rows, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(TZ)
    return df


def test_validate_clean_passes():
    df = _frame([["SPY", "2026-03-02 09:30", 100, 101, 99, 100, 10]])
    assert validate(df) == []


def test_validate_flags_bad_data():
    df = _frame([
        ["SPY", "2026-03-02 09:30", 100, 99, 98, 100, 10],   # high < open
        ["SPY", "2026-03-02 16:30", 100, 101, 99, 100, 10],  # after hours
    ])
    problems = validate(df)
    assert any("inconsistent OHLC" in p for p in problems)
    assert any("outside regular trading hours" in p for p in problems)


def test_validate_flags_missing_sessions():
    rows = [["SPY", f"2026-03-0{d} 09:30", 100, 101, 99, 100, 10] for d in (2, 3, 4)]
    rows.append(["QQQ", "2026-03-02 09:30", 100, 101, 99, 100, 10])
    assert "QQQ: missing 2 sessions" in validate(_frame(rows))
