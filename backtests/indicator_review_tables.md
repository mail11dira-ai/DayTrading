# Indicator review tables (generated)

65 sessions (2026-07-20 -> 2026-10-19), 6,500 stock-days, AI Sectors 100, as of 09:00 CT.

## Direction (market-adjusted return spread, % per day)

| Test | days | mean spread | t | % days > 0 | 1st half | 2nd half | verdict |
|---|---|---|---|---|---|---|---|
| VWAP -2 sigma vs +2 sigma (mean reversion) | 51 | -0.02 | -0.2 | 57% | -0.16 | +0.11 | no clear edge |
| VWAP below -1 sigma vs above +1 sigma (mean reversion) | 65 | -0.01 | -0.1 | 51% | -0.15 | +0.12 | no clear edge |
| RSI 5m < 30 vs > 70 (mean reversion) | 60 | +0.17 | +1.2 | 65% | +0.22 | +0.11 | no clear edge |
| Gap up vs down >= 0.5 ATR (continuation, 60m) | 34 | -0.35 | -1.5 | 41% | -0.48 | -0.22 | no clear edge |
| Gap up vs down >= 0.5 ATR (fade by the close) | 34 | +0.43 | +1.0 | 65% | +0.29 | +0.58 | no clear edge |
| 20-day momentum, top vs bottom third (60m) | 65 | -0.15 | -1.8 | 43% | -0.02 | -0.28 | no clear edge |
| 20-day momentum, top vs bottom third (to close) | 65 | -0.09 | -0.5 | 43% | +0.11 | -0.28 | no clear edge |
| First-30-min move, top vs bottom third (to close) | 65 | +0.12 | +0.8 | 54% | +0.26 | -0.03 | no clear edge |
| 5m MACD histogram > 0 vs < 0 | 65 | -0.08 | -1.1 | 42% | -0.05 | -0.10 | no clear edge |
| ADX >= 25 with +DI > -DI vs -DI > +DI | 65 | -0.15 | -1.7 | 38% | -0.20 | -0.11 | no clear edge |
| 5m RSI divergence bullish vs bearish | 65 | +0.05 | +0.5 | 51% | +0.09 | +0.01 | no clear edge |
| Squeeze fired up vs fired down | 60 | -0.17 | -2.0 | 42% | -0.21 | -0.13 | no clear edge |
| ORB confirmed up vs down (to close) | 41 | +0.47 | +1.2 | 59% | +1.20 | -0.23 | no clear edge |
| Bias BULLISH vs BEARISH (to close) | 65 | +0.08 | +0.5 | 49% | +0.41 | -0.24 | no clear edge |

## Movement (range spread, x daily ATR)

| Test | days | mean spread | t | % days > 0 | 1st half | 2nd half | verdict |
|---|---|---|---|---|---|---|---|
| RVOL top vs bottom third (next 60 min) | 65 | +0.08 | +9.8 | 95% | +0.08 | +0.08 | supported |
| RVOL top vs bottom third (rest of day) | 65 | +0.12 | +10.0 | 92% | +0.13 | +0.12 | supported |
| |gap| >= 0.5 ATR vs < 0.2 ATR (rest of day) | 64 | +0.13 | +4.6 | 75% | +0.15 | +0.12 | supported |
| Range used >= 1 ATR vs < 0.5 (next 60 min) | 51 | +0.22 | +6.1 | 96% | +0.29 | +0.15 | supported |
| ORB confirmed (either way) vs inside the range (next 60 min) | 63 | +0.09 | +7.4 | 83% | +0.09 | +0.09 | supported |
| Squeeze ON vs off (next 60 min) | 63 | -0.03 | -2.7 | 32% | -0.02 | -0.03 | INVERTED |
| Inside day / NR7 vs none (rest of day) | 65 | +0.00 | +0.2 | 42% | +0.03 | -0.02 | no clear edge |
| In-play score >= 2 vs 0 (next 60 min) | 65 | +0.15 | +9.1 | 95% | +0.17 | +0.13 | supported |
| In-play score >= 2 vs 0 (rest of day) | 65 | +0.21 | +8.6 | 92% | +0.24 | +0.18 | supported |

## In-play score buckets

| In-play score | stock-days | next-60-min range (x daily ATR) | rest-of-day range (x daily ATR) |
|---|---|---|---|
| 0 | 4492 | 0.35 | 0.58 |
| 1 | 1242 | 0.39 | 0.65 |
| 2 | 482 | 0.46 | 0.74 |
| 3+ | 276 | 0.58 | 0.92 |
