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
 - Levels: prior-day high/low/close (PDH/PDL/PDC), pre-market high/low (PMH/PML), opening range high/low (first 15 min, 8:30-8:45 CT; n/a before 8:45), classic floor pivots from the prior day (P, R1, R2, S1, S2), prior-week high/low (PWH/PWL), the prior day's volume profile (POC = highest-volume price, VAH/VAL = 70% value area, from the prior session's 5-min bars, bin = daily ATR/20), 20-day swing high/low, 52-week high/low, and round numbers within 1 daily ATR.
 - Nearest meaningful support below and resistance above current price (see WATCH LEVELS filter), each with distance in % and in ATR.
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

G. MOMENTUM & TREND STRENGTH (5-min)
 - MACD (12, 26, 9): histogram value, side (bullish > 0 / bearish < 0), expanding or fading vs the prior bar; note a histogram zero-cross in the last 30 min.
 - ADX 14 with +DI / -DI (Wilder): ADX >= 25 trending, 20-25 developing, < 20 choppy (fade breakouts, favor VWAP/level mean-reversion); direction = the larger DI.
 - TTM-style squeeze: Bollinger Bands (20, 2) inside Keltner Channels (SMA20 +/- 1.5 x ATR20) = squeeze ON (compression); "fired up/down" = squeeze ended within the last 6 bars, direction = close vs SMA20. Tested 2026-10-21: squeeze ON was followed by a quieter next hour, not a breakout (backtests/indicator_review.md).
H. DAILY COMPRESSION PATTERNS
 - Inside day (prior day's range inside the day before) and NR7 (prior day = narrowest range of the last 7): shown as context only - no extra range in testing (backtests/indicator_review.md).

I. OPENING RANGE BREAKOUT (ORB, regular session)
 - Opening ranges: first 5 / 15 / 30 minutes (high/low). The 15-minute range drives the ORB state, judged on the CURRENT position: confirmed = price is outside the range and the bar that started the breakout had >= 1.5x the normal volume for its time slot; weak = outside on light volume; failed = broke out earlier but is back inside the range; inside = no close outside yet.
J. PRE-MARKET & GAP QUALITY
 - Pre-market volume vs the average of the prior 10 pre-markets (same clock window when the run is still pre-market).
 - Gap size in daily ATRs (open vs prior close). gap-and-go = gap >= 0.3 ATR on >= 2x normal pre-market volume and still holding its side; fade risk = gap >= 1 ATR without that volume or not holding; otherwise a plain gap. Context only - not part of the bias score.
K. INTRADAY RELATIVE STRENGTH
 - Stock return over the last 15 and 30 minutes minus QQQ over the same window: leading (>= +0.3%), lagging (<= -0.3%), else in line.
L. MARKET BREADTH & REGIME (snapshot)
 - % of stocks up on the day, above VWAP and holding the daily 8/21 trend; counts of BULLISH / BEARISH bias and of stocks leading QQQ; regime = RISK-ON when the average of % up and % above VWAP (% up alone before the open) is >= 60%, RISK-OFF <= 40%, else MIXED (holding 8/21 is shown as context but not scored); plus the VIX level (calm < 15, normal < 20, elevated < 30, high).

BIAS SCORE (deterministic, -6..+6): +1 each when true, -1 when the opposite is true, 0 if n/a or neutral:
 price above VWAP | 5-min EMA9 above EMA21 | daily MA stack bullish | 5-min RSI between 55 and 70 (bearish side: between 30 and 45) | RVOL > 1.2 with up/down volume ratio > 1 (bearish side: ratio < 1) | intraday structure uptrend (bearish side: downtrend).
 Score >= +3 = BULLISH, <= -3 = BEARISH, otherwise NEUTRAL. Confirmations (0-2, shown next to the score): MACD histogram on the bias side and expanding; ADX >= 20 with the matching DI on top. Do not override the score with judgment; add any judgment as a separate one-line note.

WATCH LEVELS (research levels, not trade instructions):
 - Meaningful levels only: take every level from section C (plus VWAP and its +/-2 sigma bands); merge levels within 0.10 daily ATR of each other into one zone (use the zone midpoint, label it with all merged names); then drop any level/zone within 0.15 daily ATR of the current price. The scoreboard "Nearest S / R" column uses these meaningful levels too.
 - Bullish: trigger = first meaningful level above price. Target = first meaningful level 0.50-2.0 daily ATR above the trigger (a day-trading horizon); if none exists, target = trigger + 0.75 x daily ATR, labelled "ATR projection". Invalidation = first meaningful level below the trigger that is at least 0.25 daily ATR below it (VWAP counts if it qualifies); if none, trigger - 0.50 x daily ATR, labelled "ATR stop".
 - Bearish: mirror image (trigger = first meaningful level below price; target 0.50-2.0 ATR below the trigger; invalidation >= 0.25 ATR above the trigger).
 - Show trigger, target and invalidation with their labels, the distances in ATR units, and reward/risk = (target distance) / (invalidation distance) to 1 decimal. By construction reward >= 0.5 ATR and risk >= 0.25 ATR, so R/R is never 0 or inflated by a tiny stop. Mark R/R < 1.0 as "poor".
 - Top setups: rank by |bias score|, then confirmations, then RVOL, then the bias-side R/R; exclude setups whose bias-side R/R < 1.0 and say so if fewer remain than requested.
 Pre-market (8:00) run: VWAP, opening range, intraday EMAs and RVOL use pre-market bars where possible, otherwise "n/a (pre-market)"; lean on PDH/PDL/PDC, PMH/PML, gap and daily MAs.
```

## M. In-play (movement) score - added 2026-10-21
- Count of four flags, 0-4: RVOL >= 1.5; |gap| >= 0.5 daily ATR; range used >= 1 daily ATR; volume-confirmed 15-min ORB (either direction).
- In the 65-session test each flag predicted a bigger next-hour and rest-of-day range (in units of daily ATR) in both halves of the sample; none predicts direction. Score 0 -> 3+: next-hour range 0.35 -> 0.58 x ATR.
- Shown on every card, as a "Most in play" list (score >= 2) under Risks, and used first when ranking top setups.
- Removed from Risks: squeeze fired, inside day / NR7, 5m divergences (no edge), "range used > 1" (it means more movement, not exhaustion).

## N. Slim email (2026-10-21, cost cut)
- Everything above is still computed (and feeds the bias score, setups and lists), but each stock card now shows only:
  volume (RVOL, last-3-bar trend, top 2 spikes), VWAP (level, distance, slope, last reclaim/loss), key levels
  (PDH/PDL/PDC, PMH/PML, nearest support / resistance), opening range & gap, intraday RS vs QQQ, trend (5m EMA9/21,
  daily MA stack, RSI 5m/daily), range (ATR %, range used, in-play score), bias + confirmations, and the two watch levels.
- Dropped from the email: pivot R1/R2/S1/S2, volume profile POC/VAH/VAL, PWH/PWL, 20-day / 52-week ranges, VWAP sigma
  bands, MACD / ADX / squeeze numbers, divergence, daily pattern, up/down volume, labels on targets/stops.
  Scoreboard: the ADX column is replaced by the in-play score.
- Gmail strips <style>, class attributes and backgrounds, so the email carries only short inline styles.

## O. Market deep dive: SPY, QQQ, VIX (2026-10-23)
Section 1 of the MAG 7 email. Extra data: VIX daily history (1 year) and VIX 5-minute bars (last few sessions) via get_index_historicals.
- QQQ vs SPY: day % and 30-min return difference -> tech leading / lagging / moving together.
- Tape and breadth of the 7 stocks (regime from % up and % above VWAP).
- VIX: level, change vs prior close (pts and %), regime (calm < 15, normal < 20, elevated < 30, high), distance from its
  20-day average, 20-day range, percentile vs the last year's closes; today's open / high / low and last-30-min change.
- Warning when SPY and the VIX rise together (hedged rally) or fall together (selling without fear).
- Implied move: SPY +/- prior close x prior VIX / sqrt(252) (1 sigma), as a price band; share of the band today's range
  has used; flagged when price is outside it. QQQ estimate = VIX move x QQQ ATR% / SPY ATR%.
- Band reliability, measured each run: share of the last 250 sessions SPY closed inside the prior day's band (theory ~68%)
  and the average move as a share of the implied move.
- Full cards for SPY and QQQ with an extra "Index levels" line: pivots P/R1/R2/S1/S2, prior-day POC/VAH/VAL,
  PWH/PWL, opening range, 20-day range.
