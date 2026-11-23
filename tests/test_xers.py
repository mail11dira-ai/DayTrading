from datetime import date, datetime, time
from urllib.error import HTTPError

import pandas as pd
import pytest

from xers import levels as lvmod
from xers import report as reportmod
from xers.config import ET, window
from xers.rank import rank
from xers.sentiment import lexicon_labels, validate
from xers.tweets import cashtags, fetch_api, in_window, load_paste, make_tweet


def T(tid, handle, text, created="2026-11-24T07:00:00-05:00"):
    return make_tweet(tid, handle, created, text)


# ---------- X1 tweets ----------

def test_cashtags():
    assert cashtags("$nvda ripping, $AAPL and $NVDA again, $BRK.B, not $5 or $TOOLONGX") == ["NVDA", "AAPL", "BRK.B"]


def test_window_monday_covers_weekend():
    start, end = window(date(2026, 11, 23))                     # Monday
    assert start == datetime(2026, 11, 20, 16, 0, tzinfo=ET)    # Friday close
    assert end == datetime(2026, 11, 23, 9, 15, tzinfo=ET)


def test_in_window_handles_utc_and_offsets():
    start, end = window(date(2026, 11, 24))
    tw = [T("1", "a", "x", "2026-11-23T20:59:00Z"),             # 15:59 ET Monday -> out
          T("2", "a", "x", "2026-11-23T21:00:00Z"),             # 16:00 ET -> in
          T("3", "a", "x", "2026-11-24T09:14:00-05:00"),        # in
          T("4", "a", "x", "2026-11-24T09:15:00-05:00")]        # cutoff -> out
    assert [t["id"] for t in in_window(tw, start, end)] == ["2", "3"]


def test_load_paste(tmp_path):
    p = tmp_path / "paste.txt"
    p.write_text("@unusual_whales\ntime: 2026-11-24 07:42\nLarge call sweep $NVDA\n\n@quantdata\n$TSLA puts heavy\n")
    out = load_paste(p, default_time="2026-11-23T16:00:00-05:00")
    assert [(t["handle"], t["cashtags"]) for t in out] == [("unusual_whales", ["NVDA"]), ("quantdata", ["TSLA"])]
    assert out[0]["created_at"].startswith("2026-11-24T07:42")
    with pytest.raises(ValueError):
        p.write_text("no handle line\n$NVDA")
        load_paste(p, "2026-11-23T16:00:00-05:00")


def test_fetch_api_paginates_and_isolates_errors():
    calls = []

    def fake_get(path, params, token):
        calls.append((path, dict(params)))
        if path == "/users/by/username/bad":
            raise HTTPError(path, 404, "Not Found", None, None)
        if path.startswith("/users/by/username/"):
            return {"data": {"id": "42"}}
        if "pagination_token" not in params:
            return {"data": [{"id": "1", "created_at": "2026-11-24T12:00:00Z", "text": "$AMD calls"}],
                    "meta": {"next_token": "p2"}}
        return {"data": [{"id": "2", "created_at": "2026-11-24T12:05:00Z", "text": "$AMD again",
                          "public_metrics": {"like_count": 7}}], "meta": {}}

    start, end = window(date(2026, 11, 24))
    tweets, errors = fetch_api(start, end, handles=["good", "bad"], token="t", get=fake_get)
    assert [t["id"] for t in tweets] == ["1", "2"]
    assert tweets[1]["likes"] == 7 and tweets[0]["url"] == "https://x.com/good/status/1"
    assert "bad" in errors and "404" in errors["bad"]
    assert calls[1][1]["exclude"] == "retweets,replies"


# ---------- X2 sentiment ----------

def test_lexicon_labels():
    labels = lexicon_labels([T("1", "a", "Big call sweep on $NVDA, breakout"),
                             T("2", "b", "$TSLA downgraded, puts flowing"),
                             T("3", "c", "$AAPL earnings tonight")])
    stance = {lb["ticker"]: lb["stance"] for lb in labels}
    assert stance == {"NVDA": "bullish", "TSLA": "bearish", "AAPL": "neutral"}


def test_validate_model_labels():
    tweets = [T("1", "a", "$NVDA calls")]
    good = [{"tweet_id": "1", "ticker": "NVDA", "stance": "bullish", "confidence": 0.8, "reason": "flow"}]
    assert validate(good, tweets) == []
    bad = [{"tweet_id": "9", "ticker": "NVDA", "stance": "bullish", "confidence": 0.8},
           {"tweet_id": "1", "ticker": "AMD", "stance": "up", "confidence": 2}]
    problems = validate(bad, tweets)
    assert len(problems) == 4


# ---------- X3 rank ----------

def _lb(tid, tk, stance, conf=1.0):
    return {"tweet_id": tid, "ticker": tk, "stance": stance, "confidence": conf, "reason": ""}


def test_rank_caps_per_handle_and_uses_consensus():
    tweets = [T(str(i), "spammer", "$AAA") for i in range(5)] + [T("a", "h1", "$BBB"), T("b", "h2", "$BBB"),
                                                                T("c", "h3", "$CCC"), T("d", "h1", "$SPX")]
    labels = [_lb(str(i), "AAA", "bullish") for i in range(5)]          # one handle x5 -> capped at 1.0
    labels += [_lb("a", "BBB", "bullish"), _lb("b", "BBB", "bullish", 0.5), _lb("c", "CCC", "bearish"),
               _lb("d", "SPX", "bullish")]
    r = rank(labels, tweets)
    assert [x["ticker"] for x in r["bullish"]] == ["BBB", "AAA"]          # 1.5 > 1.0 despite fewer posts
    assert r["bullish"][1]["score"] == 1.0 and r["bullish"][1]["mentions"] == 5
    assert [x["ticker"] for x in r["bearish"]] == ["CCC"]
    assert all(x["ticker"] != "SPX" for x in r["bullish"])              # index excluded


def test_rank_top_n_and_disagreement():
    tweets = [T(f"{i}", f"h{i}", f"$T{i}") for i in range(7)] + [T("x", "hx", "$T0")]
    labels = [_lb(f"{i}", f"T{i}", "bullish", 0.1 * (i + 1)) for i in range(7)] + [_lb("x", "T0", "bearish", 0.05)]
    r = rank(labels, tweets, top_n=5)
    assert len(r["bullish"]) == 5 and r["bullish"][0]["ticker"] == "T6"
    t0 = [x for x in rank(labels, tweets, top_n=7)["bullish"] if x["ticker"] == "T0"][0]
    assert t0["handles_disagree"] == ["hx"]


# ---------- X4 levels ----------

def _bars():
    rows = []
    for ts, o, h, l, c, v in [
        ("2026-11-23 09:30", 102, 110, 101, 104, 1000),   # prior regular session: H 110
        ("2026-11-23 15:55", 104, 106, 100, 105, 1000),   # L 100, C 105
        ("2026-11-23 08:00", 103, 103, 102, 103, 50),     # prior pre-market (baseline volume 50)
        ("2026-11-24 08:00", 105, 107, 104, 106, 100),    # today pre: PMH 107 PML 104 last 106
        ("2026-11-24 09:30", 106, 120, 90, 110, 9999),    # today's regular bar must be ignored
    ]:
        rows.append(["ZZZ", pd.Timestamp(ts, tz=ET), o, h, l, c, v])
    return pd.DataFrame(rows, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])


def test_compute_levels_known_values():
    lv = lvmod.compute_levels(_bars(), date(2026, 11, 24))
    assert (lv["prev_high"], lv["prev_low"], lv["prev_close"]) == (110, 100, 105)
    assert (lv["P"], lv["R1"], lv["S1"], lv["R2"], lv["S2"]) == (105, 110, 100, 115, 95)
    assert lv["atr"] == 10
    assert (lv["PMH"], lv["PML"], lv["last"]) == (107, 104, 106)
    assert lv["gap_pct"] == pytest.approx(1 / 105)
    assert lv["pm_rvol"] == pytest.approx(2.0)


def test_plan_long_and_short():
    lv = lvmod.compute_levels(_bars(), date(2026, 11, 24))
    L = lvmod.plan(lv, "bullish")
    assert (L["entry"], L["entry_level"]) == (107, "PMH")
    assert (L["stop"], L["stop_level"]) == (105, "prev_close/P")         # highest level >= 0.15 ATR below
    assert (L["t1"], L["t1_level"], L["t2"], L["t2_level"]) == (110, "prev_high/R1", 115, "R2")
    assert L["rr_t1"] == pytest.approx(1.5) and L["shares"] == 46       # notional cap 5000/107
    S = lvmod.plan(lv, "bearish")
    assert (S["entry"], S["stop"], S["stop_level"]) == (104, 107, "PMH")
    assert (S["t1"], S["t1_level"], S["t2"]) == (100, "prev_low/S1", 95)
    assert S["side"] == "short" and S["rr_t1"] == pytest.approx(4 / 3)


def test_plan_without_premarket_uses_prior_high():
    b = _bars()
    b = b[b["timestamp"].dt.date < date(2026, 11, 24)]
    lv = lvmod.compute_levels(b, date(2026, 11, 24))
    assert lv["PMH"] is None and lv["last"] == 105
    assert lvmod.plan(lv, "bullish")["entry_level"].startswith("prev_high")


def test_no_prior_session_returns_none():
    b = _bars()
    assert lvmod.compute_levels(b[b["timestamp"].dt.date == date(2026, 11, 24)], date(2026, 11, 24)) is None


# ---------- X5 report ----------

def test_report_smoke():
    tweets = [T("1", "unusual_whales", "$ZZZ call sweep")]
    ranking = rank([_lb("1", "ZZZ", "bullish")], tweets)
    lv = lvmod.compute_levels(_bars(), date(2026, 11, 24))
    start, end = window(date(2026, 11, 24))
    md = reportmod.build(date(2026, 11, 24), start, end, tweets, ranking, {"ZZZ": lv},
                         {"ZZZ": lvmod.plan(lv, "bullish")}, "model (validated)", {}, sample=True)
    assert "SAMPLE INPUT" in md and "Not financial advice" in md
    assert "| **Entry** | 5-min close above PMH after 9:35 ET | 107.00 |" in md
    assert "No posts in window: @wallstengine" in md
    assert "## Top bearish\n\n_None._" in md
