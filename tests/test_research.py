"""Known-answer tests for the research agents' script (research/)."""
import json
import math
from datetime import date, datetime, timedelta, timezone

import pytest

from research import collect, ta
from research.analyze import CT, detect_mode
from research.report import build
from research.universe import AI_SECTORS, MAG7, ai_symbols


def test_ema_linear_series_lags_by_one():
    e = ta.ema_series([float(i) for i in range(1, 11)], 3)
    assert e[:2] == [None, None]
    assert e[2] == pytest.approx(2.0)
    assert e[-1] == pytest.approx(9.0)


def test_sma():
    assert ta.sma([1, 2, 3, 4], 2) == 3.5
    assert ta.sma([1], 2) is None


def test_rsi_extremes_and_balance():
    up = [float(i) for i in range(20)]
    assert ta.rsi_series(up, 14)[-1] == 100.0
    zig = [10, 11] * 10
    assert ta.rsi_series(zig, 14)[14] == pytest.approx(50.0)


def test_atr_constant_range():
    n = 20
    a = ta.atr_series([101.0] * n, [99.0] * n, [100.0] * n, 14)
    assert a[13] == pytest.approx(2.0) and a[-1] == pytest.approx(2.0)


def test_vwap_and_band():
    bars = [{"h": 10, "l": 10, "c": 10, "v": 1}, {"h": 20, "l": 20, "c": 20, "v": 3}]
    vw, sd = ta.vwap_series(bars)
    assert vw[-1] == pytest.approx(17.5)
    assert sd[-1] == pytest.approx(math.sqrt(18.75))


def test_vwap_event_needs_two_bars_held():
    assert ta.vwap_event([9, 11, 12], [10, 10, 10]) == ("reclaimed", 1)
    assert ta.vwap_event([9, 11, 9], [10, 10, 10]) == (None, None)
    assert ta.vwap_event([11, 9, 8], [10, 10, 10]) == ("lost", 1)


def test_floor_pivots():
    p = ta.floor_pivots(110, 90, 100)
    assert p == {"P": 100, "R1": 110, "S1": 90, "R2": 120, "S2": 80}


def test_merge_zones_merges_and_drops_near_price():
    lv = [(100.0, "A"), (100.05, "B"), (100.5, "C")]
    z = ta.merge_zones(lv, atr=1.0, price=99.0)
    assert z == [(pytest.approx(100.025), "A/B"), (100.5, "C")]
    z2 = ta.merge_zones(lv, atr=1.0, price=100.0)
    assert [lab for _, lab in z2] == ["C"]


def test_merge_zones_width_is_bounded():
    lv = [(100.0, "A"), (100.08, "B"), (100.16, "C")]  # chain would merge all three
    z = ta.merge_zones(lv, atr=1.0, price=90.0)
    assert [lab for _, lab in z] == ["A/B", "C"]


def test_watch_levels_minimum_distances():
    zones = [(98.0, "S"), (101.0, "R1"), (101.5, "R2"), (102.5, "R3")]
    w = ta.watch_levels(100.0, 2.0, zones)
    b = w["bull"]
    assert (b["trigger"], b["target"], b["stop"]) == (101.0, 102.5, 98.0)
    assert b["reward_atr"] == pytest.approx(0.75) and b["risk_atr"] == pytest.approx(1.5)
    s = w["bear"]
    assert s["trigger"] == 98.0 and s["target_label"] == "ATR projection"
    assert s["target"] == pytest.approx(96.5) and s["stop"] == 101.0
    for side in (b, s):  # never a tiny reward or stop
        assert side["reward_atr"] >= 0.5 and side["risk_atr"] >= 0.25


def test_watch_levels_atr_stop_fallback():
    w = ta.watch_levels(100.0, 2.0, [(101.0, "R")])
    assert w["bull"]["stop_label"] == "ATR stop" and w["bull"]["stop"] == pytest.approx(100.0)
    assert w["bear"] is None


def test_bias_score():
    s, lab, comp = ta.bias_score(1, True, "bullish", 60, 1.5, 2.0, "uptrend")
    assert (s, lab) == (6, "BULLISH")
    s, lab, _ = ta.bias_score(1, True, "bullish", 60, 1.5, 2.0, "uptrend", vwap_ok=False)
    assert s == 5
    s, lab, _ = ta.bias_score(-1, False, "bearish", 40, 1.5, 0.5, "downtrend")
    assert (s, lab) == (-6, "BEARISH")
    s, lab, _ = ta.bias_score(None, None, "mixed", 50, None, None, None)
    assert (s, lab) == (0, "NEUTRAL")


def test_structure_and_divergence():
    hi = [1, 3, 2, 4, 3, 5, 4]
    lo = [0, 2, 1, 3, 2, 4, 3]
    assert ta.structure(hi, lo) == "uptrend"
    assert ta.structure([5, 4, 3], [4, 3, 2]) is None
    highs = [10, 11, 12, 11, 10, 11, 11, 12, 13, 12, 11, 12]
    lows = [h - 1 for h in highs]
    rsis = [50, 60, 70, 60, 50, 55, 55, 60, 65, 60, 55, 58]
    assert ta.divergence(highs, lows, rsis) == "bearish"


def test_ma_stack_and_cross():
    assert ta.ma_stack(10, 9, 8, 7) == "bullish"
    assert ta.ma_stack(6, 7, 8, 9) == "bearish"
    assert ta.ma_stack(10, 8, 9, 7) == "mixed"
    assert ta.last_cross([1, 1, 3], [2, 2, 2], 10) == "golden"
    assert ta.last_cross([3, 3, 1], [2, 2, 2], 10) == "death"
    assert ta.last_cross([3, 3, 1] + [1] * 20, [2] * 23, 10) is None


def test_universe_unique_and_excludes_mag7():
    syms = ai_symbols()
    assert len(syms) == 59
    assert not set(syms) & set(MAG7)
    assert sum(len(t) for _, layers in AI_SECTORS for _, _, t in layers) == 63  # 59 + 4 n/a


def test_collect_reads_inline_and_saved_results(tmp_path):
    saved = tmp_path / "saved.txt"
    saved.write_text(json.dumps({"data": {"results": [
        {"symbol": "AAPL", "interval": "day", "bars": [
            {"begins_at": "2026-10-09T00:00:00Z", "open_price": "1", "close_price": "2",
             "high_price": "3", "low_price": "0.5", "volume": 10},
            {"begins_at": "2026-10-12T00:00:00Z", "open_price": "2", "close_price": "2",
             "high_price": "2", "low_price": "2", "volume": 0, "interpolated": True}]}]}}))
    quote = {"data": {"results": [{"quote": {"symbol": "AAPL", "last_trade_price": "2"}, "close": {}}]}}
    lines = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "mcp__Robinhood_Agentic__get_equity_historicals"},
            {"type": "tool_use", "id": "b", "name": "mcp__Robinhood_Agentic__get_equity_quotes"},
            {"type": "tool_use", "id": "c", "name": "mcp__Gmail__search_threads"}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "a",
             "content": f"Error: result (99 characters) exceeds maximum allowed tokens. Output has been saved to {saved}.\nFormat: JSON"},
            {"type": "tool_result", "tool_use_id": "b", "content": [{"type": "text", "text": json.dumps(quote)}]},
            {"type": "tool_result", "tool_use_id": "c", "content": json.dumps(quote)}]}},
    ]
    tr = tmp_path / "s.jsonl"
    tr.write_text("\n".join(json.dumps(x) for x in lines))
    ds = collect.load_transcript(str(tr), collect.Dataset())
    assert ds.sources == 2  # non-Robinhood result ignored
    assert [b["begins_at"] for b in ds.series("AAPL", "day")] == ["2026-10-09T00:00:00Z"]  # interpolated dropped
    assert "AAPL" in ds.quotes


def _synthetic_dataset(symbols, session):
    """12 sessions of regular 5-min bars + 300 daily bars per symbol, gently trending."""
    ds = collect.Dataset()
    days, d = [], session
    while len(days) < 12:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    days.reverse()
    for k, sym in enumerate(symbols):
        base = 100 + 10 * k
        five, px = [], base
        for di, day in enumerate(days):
            t0 = datetime(day.year, day.month, day.day, 8, 30, tzinfo=CT)
            for i in range(78):
                o = px
                px = px + (0.05 if (i + di) % 3 else -0.08)
                t = (t0 + timedelta(minutes=5 * i)).astimezone(timezone.utc)
                five.append({"begins_at": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "open_price": str(o),
                             "close_price": str(px), "high_price": str(max(o, px) + 0.05),
                             "low_price": str(min(o, px) - 0.05), "volume": 1000 + 10 * i, "session": "reg"})
        daily, dd, p = [], session - timedelta(days=430), base * 0.8
        while dd < session:
            if dd.weekday() < 5:
                p *= 1.001
                daily.append({"begins_at": f"{dd}T00:00:00Z", "open_price": str(p * 0.995),
                              "close_price": str(p), "high_price": str(p * 1.01),
                              "low_price": str(p * 0.99), "volume": 5_000_000})
            dd += timedelta(days=1)
        ds.add({"data": {"results": [{"symbol": sym, "interval": "5minute", "bars": five},
                                     {"symbol": sym, "interval": "day", "bars": daily}]}})
    return ds


@pytest.mark.parametrize("agent", ["mag7", "aisectors"])
def test_end_to_end_report_closed_session(agent):
    syms = MAG7 + ["SPY", "QQQ"] if agent == "mag7" else ai_symbols() + ["SPY", "QQQ", "SMH", "XLU"]
    session = date(2026, 10, 12)
    ds = _synthetic_dataset(syms, session)
    now = datetime(2026, 10, 13, 1, 0, tzinfo=CT)
    assert detect_mode(ds, now) == ("closed", session)
    title, html, missing, mode = build(agent, ds, now, test=True)
    assert title.startswith("[TEST]") and mode == "closed" and missing == []
    for s in syms:
        assert f"<b>{s}</b>" in html
    assert "Research only, not financial advice. No orders placed." in html
    if agent == "aisectors":
        assert "n/a - not on Robinhood" in html and "covered in AI Power Stack" in html
        assert not any(f"<b>{m}</b>" in html for m in MAG7)


def test_end_to_end_intraday_mode_uses_today():
    syms = MAG7 + ["SPY", "QQQ"]
    session = date(2026, 10, 12)
    ds = _synthetic_dataset(syms, session)
    now = datetime(2026, 10, 12, 9, 0, tzinfo=CT)  # bars after 9:00 exist in fixture but mode is driven by 'today'
    mode, sday = detect_mode(ds, now)
    assert (mode, sday) == ("intraday", session)
