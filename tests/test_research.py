import re
"""Known-answer tests for the research agents' script (research/)."""
import json
import math
from datetime import date, datetime, timedelta, timezone

import pytest

from research import collect, ta
from research.analyze import CT, detect_mode
from research.report import build
from research.universe import AI_SECTORS, MAG7, ai_symbols, modern_layout, modern_symbols


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


def test_watch_levels_target_capped_at_two_atr():
    zones = [(50.0, "52wL"), (98.0, "S"), (101.0, "R"), (130.0, "52wH")]
    w = ta.watch_levels(100.0, 2.0, zones)
    assert w["bear"]["target_label"] == "ATR projection" and w["bear"]["target"] == pytest.approx(96.5)
    assert w["bull"]["target_label"] == "ATR projection" and w["bull"]["target"] == pytest.approx(102.5)
    w2 = ta.watch_levels(100.0, 2.0, [(94.5, "S2"), (98.0, "S"), (101.0, "R")])
    assert w2["bear"]["target_label"] == "S2"  # 1.75 ATR away: within the cap


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
    assert len(syms) == 32
    assert not set(syms) & set(MAG7)
    assert {"CRWV", "NBIS", "IREN", "CIFR", "APLD"} <= set(syms)
    assert sum(len(t) for _, layers in AI_SECTORS for _, _, t in layers) == 32  # no n/a left


def test_modern_universe_dedup_and_mag7():
    syms = modern_symbols()
    assert len(syms) == 94 and len(modern_symbols("ETF")) == 34 and len(modern_symbols("Stock")) == 60
    assert not {"ARKF", "UFO", "QTUM", "ACHR", "QUBT", "LMT", "ABBV", "JETS"} & set(syms)  # day-trading screen
    assert not set(syms) & set(MAG7) and "PSTG" not in syms
    assert {"NBIS", "CRWV", "IREN"} <= set(syms)
    secs = {s["num"]: s for s in modern_layout()}
    assert len(secs) == 19 and {"TQQQ", "SOXL", "GDX", "KRE", "UAL", "SHOP", "DHI"} <= set(syms)
    assert any("NVDA" in n for n in secs["01"]["notes"]) and any("TSLA" in n for n in secs["08"]["notes"])
    assert any("VRT (in 02)" in n for n in secs["04"]["notes"]) and any("PLTR (in 03)" in n for n in secs["08"]["notes"])
    assert any("PSTG (not on Robinhood)" in n for n in secs["02"]["notes"])
    assert any("JETS (low volume)" in n and "JETS, JETS" not in n for n in secs["10"]["notes"])


def test_ai100_universe_is_100_unique_stocks():
    syms = modern_symbols(agent="ai100")
    assert len(syms) == 100 and len(set(syms)) == 100
    assert modern_symbols("ETF", agent="ai100") == [] and not set(syms) & set(MAG7)
    assert {"NBIS", "IREN", "MU", "LITE", "MSTR", "UNP", "GE"} <= set(syms)
    from research.plan import plan
    calls = plan("ai100", datetime(2026, 10, 20, 7, 59, tzinfo=CT))
    ratings = [a for t, a in calls if t.endswith("get_equity_analyst_ratings")]
    assert ratings == []  # the short AI Sectors 100 email does not use analyst ratings


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


@pytest.mark.parametrize("agent", ["mag7", "aisectors", "modern", "ai100", "super100"])
def test_end_to_end_report_closed_session(agent):
    syms = {"mag7": MAG7 + ["SPY", "QQQ"], "aisectors": ai_symbols() + ["SPY", "QQQ", "SMH", "XLU"],
            "modern": modern_symbols() + ["SPY", "QQQ"],
            "ai100": modern_symbols(agent="ai100") + ["SPY", "QQQ"],
            "super100": modern_symbols(agent="super100") + ["SPY", "QQQ"]}[agent]
    session = date(2026, 10, 12)
    ds = _synthetic_dataset(syms, session)
    now = datetime(2026, 10, 13, 1, 0, tzinfo=CT)
    assert detect_mode(ds, now) == ("closed", session)
    title, html, missing, mode = build(agent, ds, now, test=True)
    assert title.startswith("[TEST]") and mode == "closed" and missing == []
    for s in ([] if agent in ("ai100", "super100") else syms):  # compact emails: no per-sector tables
        assert f"<b>{s}</b>" in html
    assert "Research only, not financial advice. No orders placed." in html
    if agent == "aisectors":
        assert "Neo-Cloud ecosystem" in html
        assert not any(f"<b>{m}</b>" in html for m in MAG7)
    if agent == "ai100":
        assert "Weekend checklist" not in html and "ETFs Day %" not in html and "15</td>" in html
        assert ">3. Top 7 setups</h3>" in html and "Nearest S / R" not in html  # compact: no checklist, no per-sector tables, 7 setups
        assert "8/21" not in html and "20d RS" not in html and "5m RSI &gt; 75" in html  # day-trading only
    if agent == "modern":
        assert "Weekend checklist" in html and "Sector scoreboard" in html and "removed for day trading" in html
        assert "12 Neo-Cloud" in html and not any(f"<b>{m}</b>" in html for m in MAG7)
        checklist = html[html.index("Weekend checklist"):html.index(">4. ")]
        assert not any(x in checklist for x in ("SQQQ", "SOXS", "UVXY"))  # inverse products excluded


def test_end_to_end_intraday_mode_uses_today():
    syms = MAG7 + ["SPY", "QQQ"]
    session = date(2026, 10, 12)
    ds = _synthetic_dataset(syms, session)
    now = datetime(2026, 10, 12, 9, 0, tzinfo=CT)  # bars after 9:00 exist in fixture but mode is driven by 'today'
    mode, sday = detect_mode(ds, now)
    assert (mode, sday) == ("intraday", session)


def test_bullish_green_bearish_red():
    from research import render as R
    assert R.tone("bullish") == '<span class="g">bullish</span>'
    assert R.tone("uptrend") == '<span class="g">uptrend</span>'
    assert R.tone("bearish") == '<span class="r">bearish</span>'
    assert R.tone("death") == '<span class="r">death</span>'
    assert R.tone("mixed") == "mixed" and R.tone(None) == "n/a"
    assert R.score(1.5) == '<span class="p pg">+1.5</span>' and R.score(-2) == '<span class="p pr">-2.0</span>'
    assert R.score(0.1) == '<span class="p pz">+0.1</span>'
    rows = R.table(["T", "B"], [["<b>X</b>", R.score(2)], ["<b>Y</b>", R.score(-2)], ["<b>Z</b>", R.score(0)]])
    assert '<tr class="bu">' in rows and '<tr class="be">' in rows and rows.count("<tr>") == 2  # header + neutral row
    html = R.table(["Ticker", "MA stack"], [["<b>X</b>", R.tone("bullish")], ["<b>Y</b>", R.tone("bearish")]])
    assert '<td class="g">bullish</td>' in html and '<td class="r">bearish</td>' in html


def test_macd_constant_and_trend():
    _, _, h = ta.macd_series([100.0] * 60)
    assert h[-1] == pytest.approx(0.0)
    line, sig, h = ta.macd_series([100 + 0.5 * i for i in range(60)])
    assert line[-1] > 0 and h[-1] == pytest.approx(0.0, abs=1e-9)  # steady trend: line == signal
    assert h[:33] == [None] * 33 and h[33] is not None  # 26 + 9 - 2


def test_adx_pure_uptrend_is_100():
    n = 40
    hi = [101.0 + i for i in range(n)]
    lo = [99.0 + i for i in range(n)]
    cl = [100.0 + i for i in range(n)]
    adx, pdi, mdi = ta.adx_series(hi, lo, cl, 14)
    assert adx[27] == pytest.approx(100.0) and adx[26] is None
    assert pdi[-1] > 0 and mdi[-1] == 0
    adx2, pdi2, mdi2 = ta.adx_series(lo[::-1], [x - 2 for x in lo[::-1]], cl[::-1], 14)
    assert mdi2[-1] > pdi2[-1]


def test_squeeze_on_and_fired():
    n = 40
    cl = [100.0 + (0.01 if i % 2 else -0.01) for i in range(n)]
    hi, lo = [c + 1 for c in cl], [c - 1 for c in cl]  # wide bars, tiny close dispersion
    assert ta.squeeze(hi, lo, cl)[0] == "on"
    cl2 = cl[:-1] + [112.0]
    hi2, lo2 = hi[:-1] + [112.5], lo[:-1] + [111.5]
    assert ta.squeeze(hi2, lo2, cl2) == ("fired up", 1)
    assert ta.squeeze(hi[:10], lo[:10], cl[:10]) is None


def test_volume_profile_poc_and_value_area():
    bars = [{"h": 10.9, "l": 10.0, "v": 100}, {"h": 11.9, "l": 11.0, "v": 600},
            {"h": 12.9, "l": 12.0, "v": 200}, {"h": 13.9, "l": 13.0, "v": 100}]
    vp = ta.volume_profile(bars, 1.0)
    assert vp["POC"] == pytest.approx(11.5)
    assert (vp["VAL"], vp["VAH"]) == (pytest.approx(11.0), pytest.approx(13.0))  # 800/1000 >= 70%


def test_daily_pattern_and_confirmations():
    assert ta.daily_pattern([15, 16, 16, 16, 16, 16, 15.5], [10, 12, 12, 12, 12, 12, 12]) == "inside day + NR7"
    assert ta.daily_pattern([10, 12], [9, 8]) is None
    assert ta.confirmations(4, 0.2, 0.1, 30, 25, 10) == 2
    assert ta.confirmations(-4, 0.2, 0.1, 30, 25, 10) == 0
    assert ta.confirmations(-4, -0.2, -0.3, 15, 10, 25) == 0  # fading MACD, weak ADX
    assert ta.confirmations(0, 1, 0, 50, 40, 0) == 0


def test_table_tint_column_overrides_bias_pill():
    from research import render as R
    html = R.table(["S", "Day", "Bias"], [["A", R.pct(1.0), R.score(-3)], ["B", R.pct(-1.0), R.score(3)]], tint=1)
    assert html.index('<tr class="bu">') < html.index("<td>") and html.count('<tr class="bu">') == 1
    assert html.count('<tr class="be">') == 1 and "A</td>" in html.split('<tr class="be">')[0]  # row A (day +) is green


def _bar5(h, m, o, hi, lo, c, v):
    return {"t": datetime(2026, 10, 19, h, m, tzinfo=CT), "o": o, "h": hi, "l": lo, "c": c, "v": v}


def test_orb_confirmed_weak_failed_inside():
    base = [_bar5(8, 30, 100, 101, 99, 100.5, 1000), _bar5(8, 35, 100.5, 101, 99.5, 100.2, 1000),
            _bar5(8, 40, 100.2, 100.8, 99.8, 100.4, 1000)]  # 15m range 99 - 101
    slot = {datetime(2026, 10, 19, 8, 45, tzinfo=CT).time(): 1000.0}
    assert ta.orb_status(base, 3, slot) is None  # range not complete yet
    inside = base + [_bar5(8, 45, 100.4, 100.9, 100.0, 100.5, 900)]
    assert ta.orb_status(inside, 3, slot)["state"] == "inside"
    up_vol = base + [_bar5(8, 45, 100.5, 102.5, 100.5, 102.0, 2500)]
    o = ta.orb_status(up_vol, 3, slot)
    assert (o["state"], o["dir"], o["time"]) == ("confirmed", "up", "08:45") and o["volx"] == pytest.approx(2.5)
    assert ta.orb_status(base + [_bar5(8, 45, 100.5, 102.5, 100.5, 102.0, 1100)], 3, slot)["state"] == "weak"
    failed = up_vol + [_bar5(8, 50, 102.0, 102.1, 100.0, 100.3, 1000)]  # closed back inside the range
    fo = ta.orb_status(failed, 3, slot)
    assert (fo["state"], fo["dir"]) == ("failed", "up")
    flip = failed + [_bar5(8, 55, 100.3, 100.4, 97.0, 97.5, 2200)]  # first break failed, later breakdown on volume
    f = ta.orb_status(flip, 3, {**slot, datetime(2026, 10, 19, 8, 55, tzinfo=CT).time(): 1000.0})
    assert (f["state"], f["dir"], f["time"]) == ("confirmed", "down", "08:55")
    down = base + [_bar5(8, 45, 99.5, 99.6, 97.5, 98.0, 3000)]
    assert (ta.orb_status(down, 3, slot)["state"], ta.orb_status(down, 3, slot)["dir"]) == ("confirmed", "down")


def test_gap_quality_and_window_return():
    assert ta.gap_quality(0.2, 5, True) is None and ta.gap_quality(None, 5, True) is None
    assert ta.gap_quality(0.8, 2.5, True) == ("go", "up")
    assert ta.gap_quality(-0.8, 2.5, True) == ("go", "down")
    assert ta.gap_quality(1.5, 1.0, True) == ("fade", "up")   # big gap, no pre-market volume
    assert ta.gap_quality(1.5, 3.0, False) == ("fade", "up")  # big gap, volume but not holding
    assert ta.gap_quality(0.5, 1.0, False) == ("gap", "up")
    assert ta.gap_quality(0.8, None, True) == ("gap", "up")
    assert ta.window_return([100, 101, 102, 103], 99, 2) == pytest.approx((103 / 101 - 1) * 100)  # 103 vs 101
    assert ta.window_return([100, 101], 99, 6) == pytest.approx((101 / 99 - 1) * 100)  # short series: from open
    assert ta.window_return([], 99, 3) is None


def test_collect_reads_index_quotes():
    ds = collect.Dataset()
    ds.add({"data": {"quotes": [{"instrument_id": "x", "symbol": "VIX", "value": "18.44", "state": ""}]}})
    assert ds.indexes == {"VIX": pytest.approx(18.44)}
    ds.add({"data": {"quotes": [{"symbol": "VIX", "value": ""}]}})  # restricted / empty values are ignored
    assert ds.indexes["VIX"] == pytest.approx(18.44)


def test_report_has_breadth_rs_and_orb_sections():
    syms = MAG7 + ["SPY", "QQQ"]
    ds = _synthetic_dataset(syms, date(2026, 10, 12))
    ds.indexes["VIX"] = 18.4
    title, html, missing, mode = build("mag7", ds, datetime(2026, 10, 13, 1, 0, tzinfo=CT), test=True)
    assert "Breadth (7 stocks)" in html and "<b>VIX 18.40</b> (normal;" in html
    assert "Market deep dive (SPY, QQQ, VIX)" in html and "<b>Index levels:</b>" in html and "QQQ vs SPY:" in html
    assert "Intraday RS:" in html and "<b>Open &amp; gap:</b>" in html and "pre-mkt vol" in html
    assert "ORB confirmed (15m range" in html and "Intraday RS leaders" in html


def test_breadth_regime_ignores_daily_hold():
    from research.report import _breadth
    base = {"ok": True, "thin": False, "vwap": 100.0, "bias_label": "BULLISH", "rs30": 0.5}
    res = {s: dict(base, day_pct=1.0, price=101.0, hold_821="lost") for s in "ABCDE"}
    line = _breadth(res, list(res), None)[0]
    assert "0% holding 8/21" in line and "RISK-ON" in line  # 100% up + above VWAP, hold not scored
    res = {s: dict(r, day_pct=-1.0, price=99.0, hold_821="holding") for s, r in res.items()}
    assert "RISK-OFF" in _breadth(res, list(res), None)[0]


def test_plan_uses_one_extended_5min_pull_and_vix():
    from research.plan import plan, VIX_ID
    calls = plan("ai100", datetime(2026, 10, 20, 7, 59, tzinfo=CT))
    five = [a for t, a in calls if t.endswith("get_equity_historicals") and a["interval"] == "5minute"]
    assert five and all(a["bounds"] == "extended" and a["start_time"] == "2026-10-06T08:00:00Z" for a in five)
    assert max(len(a["symbols"]) for a in five) == 10  # the tool's per-call limit
    assert len(calls) == 30 and calls[-1][1] == {"instrument_ids": [VIX_ID]}  # 10 symbols per 5-minute call, no ratings for ai100


def test_validate_stats_helpers():
    from research import validate as V
    assert V.tstat([1, 1, 1]) is None  # zero variance
    assert V.tstat([1.0, 2.0]) is None  # too few
    assert V.tstat([1.0, 2.0, 3.0, 2.0]) == pytest.approx(2.0 / (math.sqrt(2 / 3) / 2))  # mean 2, sd sqrt(2/3), n 4
    days = [date(2026, 9, d) for d in range(1, 21)]
    good = {d: 0.5 + (0.05 if i % 2 else -0.05) for i, d in enumerate(days)}
    assert V.verdict(good)["verdict"] == "supported"
    assert V.verdict({d: -x for d, x in good.items()})["verdict"] == "INVERTED"
    assert V.verdict({d: -x for d, x in good.items()}, expect=-1)["verdict"] == "supported"
    noisy = {d: (1 if i % 2 else -1) * 0.5 for i, d in enumerate(days)}
    assert V.verdict(noisy)["verdict"] == "no clear edge"
    assert V.verdict({days[0]: 1.0})["verdict"] == "too few days"
    rows = [{"day": date(2026, 9, 1), "adj60": 1.0, "k": 1}, {"day": date(2026, 9, 1), "adj60": 0.5, "k": 1},
            {"day": date(2026, 9, 1), "adj60": -1.0, "k": 0}, {"day": date(2026, 9, 1), "adj60": -0.5, "k": 0}]
    assert V.day_spread(rows, lambda r: r["k"] == 1, lambda r: r["k"] == 0) == {date(2026, 9, 1): pytest.approx(1.5)}
    assert V.day_spread(rows, lambda r: r["k"] == 1, lambda r: r["k"] == 0, min_side=3) == {}


def test_validate_asof_view_has_no_lookahead_and_builds_samples():
    from research import validate as V
    syms = ai_symbols() + ["SPY", "QQQ"]
    session = date(2026, 10, 12)
    ds = _synthetic_dataset(syms, session)
    cache = V.Cache(ds, syms)
    cut = datetime(2026, 10, 12, 8, 55, tzinfo=CT).astimezone(timezone.utc).strftime(V.FMT)
    view = V.AsOf(cache, cut, "2026-09-20T00:00:00Z")
    bars = view.series("SPY", "5minute")
    assert bars and max(b["begins_at"] for b in bars) == cut  # last included bar is the 08:55 bar
    assert view.quotes == {}
    samples, days = V.build_samples(ds)
    assert days and {s["day"] for s in samples} == set(days)  # 12 sessions -> 2 asof days with 10 prior
    s0 = samples[0]
    assert {"bias", "comp", "adj60", "adjc", "rs30", "orb", "conf"} <= set(s0)
    text, results, _ = V.report(samples, days)
    assert "Bias score & signal validation" in text and "too few days" in text  # only 2 days: honest verdict


def test_only_bullish_bearish_words_are_coloured():
    from research.render import words_only
    html = ('<tr class="bu"><td class="g">+1.20%</td><td><span class="r">-0.5%</span> lost VWAP</td>'
            '<td><span class="p pr">-3 BEARISH</span></td><td><span class="p pg">+0.8</span></td></tr>'
            '<div class="k kg">MACD <span class="g">bullish</span>, stack bearish</div>')
    out = words_only(html)
    assert 'class="bu"' not in out and 'class="k kg"' not in out and '<td class="g">' not in out
    assert "-0.5% lost VWAP" in out and '<span class="p pz">+0.8</span>' in out
    assert '<span class="p pr">-3 BEARISH</span>' in out  # pill keeps colour only because it says BEARISH
    assert '<span class="g">bullish</span>' in out and '<span class="r">bearish</span>' in out
    assert out.count('class="g"') == 1 and out.count('class="r"') == 1


def test_colours_are_inline_for_gmail():
    from research.render import doc
    html = doc("T", "n", '<p><span class="g">bullish</span> <span class="r">bearish</span> +1.2%</p>'
                         '<table border="1"><tr><td>1</td></tr></table>')
    assert '<span style="color:#0a7d2c;font-weight:bold">bullish</span>' in html
    assert '<span style="color:#c0392b;font-weight:bold">bearish</span>' in html
    assert "+1.2%</p>" in html  # numbers stay plain
    # Gmail strips <style> and class attributes, so the sent email carries neither
    assert "<style>" not in html and "class=" not in html


def test_inline_html_readable_without_backgrounds():
    from research.render import doc
    html = doc("T", "n", '<table border="1"><tr><th class="l">A</th><th>B</th></tr></table>')
    assert "color:#fff" not in html and "background" not in html


def test_in_play_score_counts_movement_flags():
    from research.ta import in_play
    assert in_play(None, None, None, None) == (0, [])
    n, why = in_play(1.8, -0.7, 1.2, {"state": "confirmed", "dir": "up"})
    assert n == 4 and why == ["RVOL 1.8", "gap 0.7 ATR", "range used 1.2 ATR", "ORB up confirmed"]
    assert in_play(1.49, 0.49, 0.99, {"state": "failed", "dir": "up"})[0] == 0  # thresholds are inclusive at 1.5/0.5/1.0


def test_report_lists_in_play_and_drops_untested_breakout_lists():
    syms = MAG7 + ["SPY", "QQQ"]
    ds = _synthetic_dataset(syms, date(2026, 10, 12))
    title, html, missing, mode = build("mag7", ds, datetime(2026, 10, 13, 1, 0, tzinfo=CT), test=True)
    assert "Most in play" in html and "<b>in play " in html
    assert "Squeeze fired" not in html and "Inside day / NR7 (breakout watch)" not in html and "5m divergences" not in html
    assert "breakout pending" not in html


def test_vix_implied_move_and_band_hit_rate():
    from research import market as M
    assert M.implied_move_pct(15.874) == pytest.approx(1.0, abs=1e-3)  # 15.874 / sqrt(252) = 1%
    d = [date(2026, 1, 1) + timedelta(days=i) for i in range(41)]
    spy = [(x, 100.0 * (1.005 if i % 2 else 1.0)) for i, x in enumerate(d)]  # alternating +0.5% / -0.5% days
    vix = {x: 15.874 for x in d}  # implied 1% a day
    hit, ratio, n = M.band_hit_rate(spy, vix)
    assert n == 40 and hit == 100.0 and ratio == pytest.approx(0.5, abs=0.01)
    assert M.band_hit_rate(spy[:10], vix) is None  # too few days


def test_vix_analysis_from_index_bars():
    from research import collect
    from research import market as M
    ds = collect.Dataset()
    day = lambda d, c: {"begins_at": f"{d}T00:00:00Z", "open_value": str(c), "high_value": str(c), "low_value": str(c), "close_value": str(c)}
    ds.add({"data": {"results": [{"symbol": "VIX", "interval": "day",
                                  "bars": [day(f"2026-09-{i:02d}", 15 + i % 3) for i in range(1, 29)]
                                  + [day("2026-10-01", 99) | {"interpolated": True}]}]}})
    five = [{"begins_at": f"2026-10-01T{13 + (30 + 5 * i) // 60:02d}:{(30 + 5 * i) % 60:02d}:00Z", "open_value": "18",
             "high_value": str(18 + i * 0.1), "low_value": "17.5", "close_value": str(18 + i * 0.1)} for i in range(12)]
    ds.add({"data": {"results": [{"symbol": "VIX", "interval": "5minute", "bars": five}]}})
    v = M.vix_analysis(ds, date(2026, 10, 1))
    assert v["prev"] == 16.0 and v["level"] == pytest.approx(19.1) and v["open"] == 18.0  # interpolated daily bar ignored
    assert v["chg"] == pytest.approx(3.1) and v["chg30"] == pytest.approx(0.6) and v["regime"] == "normal"
    assert v["em_pct"] == pytest.approx(16 / 252 ** 0.5)


def test_mag7_plan_fetches_vix_history():
    from research.plan import plan, VIX_ID
    calls = plan("mag7", datetime(2026, 10, 23, 7, 59, tzinfo=CT))
    idx = [a for t, a in calls if t.endswith("get_index_historicals")]
    assert [a["interval"] for a in idx] == ["day", "5minute"] and all(a["instrument_ids"] == [VIX_ID] for a in idx)
    assert not any(t.endswith("get_index_historicals") for t, _ in plan("ai100", datetime(2026, 10, 23, 7, 59, tzinfo=CT)))



def test_super100_universe_and_report():
    from research.plan import plan
    from research.universe import symbols
    syms, bench = symbols("super100")
    assert len(syms) == 100 == len(set(syms)) and set(MAG7) <= set(syms) and "BRK.B" in syms and "SPCX" in syms
    assert {"ABBV", "RTX", "LMT"} <= set(syms)  # the user's list is not day-trading screened
    calls = plan("super100", datetime(2026, 10, 27, 8, 30, tzinfo=CT))
    assert sum(t.endswith("get_index_historicals") for t, _ in calls) == 2
    ds = _synthetic_dataset(syms + bench, date(2026, 10, 12))
    title, html, missing, mode = build("super100", ds, datetime(2026, 10, 13, 1, 0, tzinfo=CT), test=True)
    assert title.startswith("[TEST] Super 100 Research") and missing == []
    assert "Market deep dive (SPY, QQQ, VIX)" in html and "Sector scoreboard" in html and "Top 3 setups" in html and "Weekend checklist" not in html
