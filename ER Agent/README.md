# ER Research Agent

Research only - no orders. Emails mail11dira@gmail.com Mon-Fri at 8:10 am and 1:10 pm CT (the 8:10 run is before the open; the 1:10 run is after the open, so
before-the-open reporters show their real reaction). Code: `research/er.py` (tests in `tests/test_research.py`).

**What it does:** takes every large-cap (> $1B) company reporting earnings today from the Robinhood calendar,
keeps the liquid ones (price >= $10, >= $300M traded per day, >= 2M shares per day; technical filters: ATR14 >= 1.5% of price, RSI14 between 25 and 75; context filter: prior session moved <= 10%), scores the 15 most liquid with a fixed-weight
checklist and always emails the top 5 Bullish and top 5 Bearish names (the highest and lowest scores in scope), plus a trade plan for each.
A name that fails a liquidity, technical or context filter is still shown when it is in the top or bottom 5, marked "partial data".

**Technicals (computed in code from the daily bars, no extra Robinhood calls):**
- Trend: 50-day and 200-day averages; MACD (12/26/9) histogram.
- Bollinger Bands (20, 2 sd): %B position and band width.
- VWAP: rolling 20-session VWAP; price above or below it.
- Volume flow: up-volume vs down-volume ratio and on-balance volume (OBV) over 20 sessions; RVOL vs the 20-day average.
- Levels: 20- and 60-day support and resistance; classic pivots (P, R1, S1) from the last session.
- Each of VWAP, 200-day average, MACD and volume flow adds +1 or -1 to the score (the Bullish/Bearish cut-offs stay at +2/-2).
- Options (one market scan per report date, about +$0.01-0.03 per run): call share of options premium (above 65% = +1, below 35% = -1, added to the score); implied volatility (IV30) with the implied daily move; IV rank (shown, not scored: high IV means expensive options); put/call volume.
- The options scan covers reporters with a market cap of $10B or more.

**Which names each run covers:**
- **8:10 am run:** today's before-the-open (BMO) and after-the-close (AMC) reporters.
- **1:10 pm run:** today's AMC reporters and tomorrow's BMO reporters (today's BMO have already reported).

**Stages** (each prints the read-only Robinhood calls for the next; symbols depend on the day's calendar):
1. `python3 -m research.er calendar` - today's earnings calendar (1 call)
2. `python3 -m research.er screen` - 130 days of daily bars for every reporter + SPY (~25-30 calls)
3. `python3 -m research.er detail` - quotes, analyst ratings, 2 years of daily bars and the 8-quarter EPS
   history for the 15 most liquid names (~19 calls)
4. `python3 -m research.er report --out /tmp/er_report.html` - builds the email

**Score** (points; total >= +2 Bullish, <= -2 Bearish):

| Factor | Rule | Points |
|---|---|---|
| Reaction (reported names only) | move since the prior close in daily-ATR units: >= 1 / 0.5 / 0.2 | +3 / +2 / +1 (same negative) |
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

**Most traded and biggest (section 4 of the email):** the top 5 reporters in scope on four lenses, all names with data (not only the
screened ones): highest share volume (20-day average), most liquid (20-day average dollar volume), most popular (options contracts
traded on the day, calls + puts from the scan) and biggest (market cap). The scan covers $10B+ names only, so the popular and biggest
columns rank only those.

**Trade plan (rule-based levels, next session):** Bullish: entry = break of the prior session's high; stop = the tighter of 20-day support or 1 ATR below the entry; Target 1 = 20-day resistance (or 1.5 ATR); Target 2 = 2.5 ATR. Bearish mirrors this from the prior low. The reward-to-risk ratio is shown. These are levels to watch, not advice; the email says so.
