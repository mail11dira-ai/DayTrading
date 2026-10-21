# Indicator review (2026-10-21)

Question: which day-trading indicators in the MAG 7 / AI Sectors 100 agents carry real information at the 8:59 CT
run, and which should be added or removed? Data: the same 65 sessions (2026-07-20 -> 2026-10-19, 6,500 stock-days,
AI Sectors 100) used in `bias_validation.md`; the as-of view uses only bars completed by 09:00 CT (no look-ahead).
Fixed textbook thresholds, nothing tuned. Full tables: `indicator_review_tables.md`
(`PYTHONPATH=. python3 -m research.indicator_review`).

## What the data says
1. **Direction: nothing works.** 14 direction tests (VWAP +/-1 and 2 sigma reversion, RSI extremes, gap continuation
   and gap fade, 20-day momentum, first-30-min momentum, MACD, ADX/DMI, RSI divergence, squeeze direction, ORB
   direction, the bias score to the close) - all "no clear edge" for the next hour or the close. This matches
   `bias_validation.md`: at 9:00 CT these indicators describe what already happened.
2. **Movement: four measures work strongly, in both halves of the sample.** RVOL (t = +9.8), gap >= 0.5 ATR
   (t = +4.6), range used >= 1 ATR (t = +6.1, volatility persists - it is *not* exhaustion) and a volume-confirmed
   opening-range breakout in either direction (t = +7.4) all predict a bigger next-hour and rest-of-day range.
3. **Two "breakout" claims were wrong.** TTM squeeze ON was followed by a *quieter* next hour (INVERTED, t = -2.7),
   and inside day / NR7 gave no extra range (t = +0.2).

## Changes made (both agents)
| Change | Why |
|---|---|
| **Added** in-play score 0-4 (RVOL >= 1.5, gap >= 0.5 ATR, range used >= 1 ATR, ORB confirmed) on every card, as a "Most in play" list, and in each top setup | 0 -> 3+ flags: next-hour range 0.35 -> 0.58 x ATR, rest of day 0.58 -> 0.92 x ATR (t = +9.1) |
| **Changed** top-setup ranking: in-play score first, then bias, confirmations, RVOL, R/R | traders need stocks that move; bias did not predict direction anyway |
| **Removed** risk lists: "Squeeze fired", "Inside day / NR7 (breakout watch)", "5m divergences" | no edge (squeeze ON inverted); shorter email |
| **Removed** "Range used > 1" from risks (it implied exhaustion) | range used >= 1 means *more* movement; now an in-play flag |
| **Reworded** card text: squeeze "breakout pending" and NR7 "breakout watch" | the data contradicts both claims |
| **Kept** bias score unchanged (user decision 2026-10-20), VWAP/levels/MAs/RSI/MACD/ADX/ORB/RS as chart description | descriptive context; not presented as forecasts |

## Caveats
- The four flags were each tested on these 65 sessions and then combined, so the in-play *combination* is
  in-sample; each flag held in both halves. Re-check on new sessions (`research.indicator_review`) after ~60 more.
- Movement is measured in units of each stock's daily ATR, so it is not just "volatile stocks are volatile".
- Pre-market volume could not be tested at the 9:00 cut (only ~900 stock-days carry it); it stays as context.
