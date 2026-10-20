# Bias score & signal validation

Universe: AI Sectors 100 (100 stocks). Sessions tested: **65** (2026-07-20 -> 2026-10-19), run time 09:00 CT (the 8:59 run), 6,500 stock-days. Returns are **market-adjusted** (stock minus QQQ over the same window), in %. Rules are measured as-is, not tuned.

How to read: a *spread* is the average return of stocks with the signal on minus stocks with the opposite signal, computed per day and judged across days (t-stat, % of days positive, first half vs second half of the sample). **supported** = t >= 2 and positive in both halves; **INVERTED** = t <= -2 and negative in both halves; otherwise **no clear edge**. With ~12 tests, one or two |t| of 2-3 can appear by chance.

## 0. Component activity at 09:00 CT (share of stock-days)

| Component | bullish (+1) | bearish (-1) | neutral (0) |
|---|---|---|---|
| price vs VWAP | 45% | 55% | 0% |
| 5m EMA 9/21 | 48% | 52% | 0% |
| daily MA stack | 21% | 33% | 46% |
| 5m RSI zone | 23% | 25% | 53% |
| volume | 13% | 13% | 74% |
| intraday structure | 0% | 0% | 99% |

## 1. Bias score buckets

| Bias | N | Next 60 min: mean adj % | hit rate | To close: mean adj % |
|---|---|---|---|---|
| <= -3 BEARISH | 1588 | +0.04 | 51% | -0.01 |
| -2 .. -1 | 1569 | -0.00 | 51% | -0.13 |
| 0 | 750 | -0.05 | n/a | -0.13 |
| +1 .. +2 | 1415 | -0.02 | 48% | +0.09 |
| >= +3 BULLISH | 1178 | -0.10 | 45% | -0.06 |

## 2. Signal tests (spread of next-60-min market-adjusted return, % per day)

*Control (should be strongly positive, it is not a forecast): the trailing 30-minute move vs QQQ of BULLISH minus BEARISH stocks averages +3.66% (t = +26.4) - the score does describe what the stock has just done; the tests below ask whether that continues.*

| Signal | days | mean spread | t | % days > 0 | 1st half | 2nd half | verdict |
|---|---|---|---|---|---|---|---|
| **Bias >= +3 vs <= -3** (the headline score) | 65 | -0.13 | -1.2 | 42% | +0.01 | -0.26 | no clear edge |
| Bias >= +1 vs <= -1 | 65 | -0.06 | -0.8 | 43% | +0.02 | -0.14 | no clear edge |
| Component: price vs VWAP | 65 | +0.03 | +0.4 | 49% | +0.14 | -0.07 | no clear edge |
| Component: 5m EMA 9 vs 21 | 65 | -0.07 | -0.9 | 45% | -0.05 | -0.10 | no clear edge |
| Component: daily MA stack | 65 | -0.18 | -1.9 | 34% | +0.01 | -0.36 | no clear edge |
| Component: 5m RSI zone | 65 | -0.04 | -0.6 | 48% | +0.03 | -0.11 | no clear edge |
| Component: volume (RVOL > 1.2 + up/down) | 65 | -0.02 | -0.2 | 51% | +0.06 | -0.10 | no clear edge |
| Component: intraday structure | 0 | n/a | n/a | n/a | n/a | n/a | too few days |
| ORB confirmed up vs confirmed down | 41 | -0.05 | -0.2 | 46% | +0.57 | -0.64 | no clear edge |
| ORB failed up vs failed down (expect <0) | 40 | +0.19 | +1.0 | 52% | +0.44 | -0.06 | no clear edge |
| Intraday RS: leading (>= +0.3%) vs lagging (<= -0.3%) | 65 | +0.01 | +0.1 | 49% | +0.14 | -0.11 | no clear edge |
| Holding 8/21 trend vs below EMA21 | 65 | -0.16 | -2.2 | 35% | -0.02 | -0.30 | INVERTED |

## 3. Confirmations and the top-5 ranking

Direction-adjusted return (long if bullish, short if bearish), stocks with |bias| >= 3:

| MACD/ADX confirmations | N | mean adj % (next 60 min) | hit rate |
|---|---|---|---|
| 0 | 198 | +0.02 | 51% |
| 1 | 1377 | -0.10 | 47% |
| 2 | 1191 | -0.03 | 49% |

Top-5 setups (ranked by |bias|, confirmations, RVOL, R/R), direction-adjusted next-60-min return per day: mean **-0.06%** over 65 days (t = -0.6); all qualifying setups: -0.04% (t = -0.7).

## 4. Summary

- **Supported (t >= 2, both halves positive):** none
- **Inverted (worked backwards):** Holding 8/21 trend vs below EMA21
- **No clear edge:** **Bias >= +3 vs <= -3** (the headline score); Bias >= +1 vs <= -1; Component: price vs VWAP; Component: 5m EMA 9 vs 21; Component: daily MA stack; Component: 5m RSI zone; Component: volume (RVOL > 1.2 + up/down); ORB confirmed up vs confirmed down; ORB failed up vs failed down (expect <0); Intraday RS: leading (>= +0.3%) vs lagging (<= -0.3%)

Not testable here: pre-market volume and gap quality (needs pre-market history for every past session); they are shown in the email as context only and are **not** part of the bias score or the ranking.
