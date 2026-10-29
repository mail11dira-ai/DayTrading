# ER Research Agent

Research only - no orders. Emails mail11dira@gmail.com Mon-Fri at 8:15 CT (before the open, after most
before-the-open reports). Code: `research/er.py` (tests in `tests/test_research.py`).

**What it does:** takes every large-cap (> $1B) company reporting earnings today from the Robinhood calendar,
keeps the liquid ones (price >= $10, >= $300M traded per day), scores the 15 most liquid with a fixed-weight
checklist and emails the top 5 with a Bullish / Bearish / Neutral call.

**Stages** (each prints the read-only Robinhood calls for the next; symbols depend on the day's calendar):
1. `python3 -m research.er calendar` - today's earnings calendar (1 call)
2. `python3 -m research.er screen` - 130 days of daily bars for every reporter + SPY (~25-30 calls)
3. `python3 -m research.er detail` - quotes, analyst ratings, 2 years of daily bars and the 8-quarter EPS
   history for the 15 most liquid names (~19 calls)
4. `python3 -m research.er report --out /tmp/er_report.html` - builds the email

**Score** (points; total >= +2 Bullish, <= -2 Bearish):

| Factor | Rule | Points |
|---|---|---|
| Reaction (reported names only) | pre-market gap in daily-ATR units: >= 1 / 0.5 / 0.2 | +3 / +2 / +1 (same negative) |
| EPS surprise | actual vs estimate >= +5% / <= -5% | +1 / -1 |
| Beat rate | last 8 reports beat the estimate >= 75% / <= 40% | +1 / -1 |
| Reaction history | up day after past reports >= 75% / <= 25% | +1 / -1 |
| Momentum | 20-day return vs SPY > +5% / < -5% | +1 / -1 |
| Trend | close above / below the 50-day average | +1 / -1 |
| Analysts | buy >= 70% and target >= +10% / buy < 40% or target below price | +1 / -1 |

**Caveats:** nothing is tuned and nothing is validated out of sample. Post-earnings direction is close to a coin
flip. After-the-close (AMC) names have no reaction yet, so their call rests on history, trend and analysts only.
The email shows each name's average past earnings move so position size can match the risk.

First live test (2026-10-29 data, overnight quotes): 245 reporters, 15 scored; top 5 MA, LLY, LIN Bullish,
COIN, INTC Bearish.
