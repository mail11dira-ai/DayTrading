# Day-trading technical analysis (shared by MAG 7 and AI Sectors)

This exact text is embedded in both routine prompts. All numbers are computed in Python from Robinhood bars; the bias score is a fixed rule, not model judgment.

```
DAY-TRADING TECHNICAL ANALYSIS (compute every number in python from Robinhood bars - never estimate by eye; save raw bars to files first).
Bars needed per symbol: today's 5-minute bars incl. extended hours (pre-market), the prior 10 sessions of 5-minute bars, ~12 months of daily bars. Regular session = 8:30-15:00 CT. If a value can't be computed (e.g. no regular-session bars yet), show "n/a" - never invent it.

A. VOLUME
 - RVOL = today's cumulative regular-session volume / average cumulative volume at the same time of day over the prior 10 sessions (pre-market run: pre-market volume vs prior 10 pre-markets).
 - Volume trend: last 3 five-minute bars' volume vs the session's average 5-min volume (rising / falling).
 - Up/down volume ratio: volume on green 5-min bars / volume on red 5-min bars today.
 - Flag any 5-min bar with volume > 3x the 10-day average for that time slot (volume spike) and its price direction.
B. VWAP
 - Session VWAP from 8:30 CT using typical price (H+L+C)/3 x volume; +/-1 and +/-2 standard-deviation bands.
 - Price vs VWAP in % and in daily-ATR units; VWAP slope over the last 30 minutes (up / flat / down).
 - Events: reclaimed VWAP (crossed above and held 2+ bars) or lost VWAP (crossed below and held 2+ bars) today.
C. SUPPORT / RESISTANCE & PRICE ACTION
 - Levels: prior-day high/low/close (PDH/PDL/PDC), pre-market high/low (PMH/PML), opening range high/low (first 15 min, 8:30-8:45 CT; n/a before 8:45), classic floor pivots from the prior day (P, R1, R2, S1, S2), 20-day swing high/low, 52-week high/low, and round numbers within 1 daily ATR.
 - Nearest support below and nearest resistance above current price (from the levels above), each with distance in % and in ATR.
 - Gap % = today's open (or pre-market price) vs PDC; gap filled yes/no.
 - Intraday structure from 5-min swing points: higher highs + higher lows (uptrend), lower highs + lower lows (downtrend), or range. Note an opening-range breakout/breakdown or a break of PDH/PDL/PMH/PML.
D. MOVING AVERAGES
 - Intraday (5-min): EMA 9, EMA 21; cross state and any cross in the last 30 min.
 - Daily: EMA 9, EMA 21, SMA 20, SMA 50, SMA 200. MA stack: bullish if price > EMA9 > EMA21 > SMA50, bearish if the reverse, else mixed. Note golden/death cross (SMA50 vs SMA200) within the last 10 sessions.
E. RSI (Wilder, 14)
 - RSI on 5-min bars and on daily bars. Zones: >70 overbought, <30 oversold, 50 line = momentum pivot.
 - Divergence flag (5-min): price makes a higher high while RSI makes a lower high (bearish), or a lower low with a higher RSI low (bullish), over the last 12 bars.
F. ATR (Wilder, 14)
 - Daily ATR14 and ATR % of price; 5-min ATR14.
 - Range used = today's (high - low) / daily ATR14 (above 1.0 = extended, less room left).
 - Expected range from here: current price +/- (daily ATR14 - today's range so far), floored at 0.

BIAS SCORE (deterministic, -6..+6): +1 each when true, -1 when the opposite is true, 0 if n/a or neutral:
 price above VWAP | 5-min EMA9 above EMA21 | daily MA stack bullish | 5-min RSI between 55 and 70 (bearish side: between 30 and 45) | RVOL > 1.2 with up/down volume ratio > 1 (bearish side: ratio < 1) | intraday structure uptrend (bearish side: downtrend).
 Score >= +3 = BULLISH, <= -3 = BEARISH, otherwise NEUTRAL. Do not override the score with judgment; add any judgment as a separate one-line note.

WATCH LEVELS (research levels, not trade instructions):
 - Bullish above: the nearest resistance; next target: the following resistance or VWAP +2 sigma; invalidation: nearest support or VWAP, whichever is closer below.
 - Bearish below: the nearest support; next target: the following support or VWAP -2 sigma; invalidation: nearest resistance or VWAP, whichever is closer above.
 - Show the move to target and to invalidation in ATR units (reward/risk ratio to 1 decimal).
 Pre-market (8:00) run: VWAP, opening range, intraday EMAs and RVOL use pre-market bars where possible, otherwise "n/a (pre-market)"; lean on PDH/PDL/PDC, PMH/PML, gap and daily MAs.
```
