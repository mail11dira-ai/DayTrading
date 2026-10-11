# iter_3

**Change:** relative-volume filter (`min_rvol=1.0`, 10-session lookback) on baseline ORB 30m.

**Hypothesis:** breakouts only follow through in stocks trading above normal volume ("stocks in play").

**Train-only tuning** (test untouched): rvol off Sharpe -0.48, 1.0 → 1.55, 1.5 → 0.88, 2.0 → -1.47, 3.0 → -1.10. 1.0 chosen.

**Confound check:** the filter needs 10 sessions of history, so it skips the first 10 sessions of each window. Baseline on train sessions 11-112 alone: Sharpe -0.48 (unchanged), so warm-up does not explain the gain. In the test window the filter can only trade the last 38 of 48 sessions.

Config: $25,000 start, slippage 0.02%/side, $0 commission, risk limits from `src/risk.py` defaults.

## train: 2026-02-23 → 2026-08-03 (112 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +9.90% | 1.54 | 9.23% | 1 | 100.0% | inf | +2480.26 |
| ORB 30m (baseline) | -2.12% | -0.48 | 7.18% | 410 | 47.3% | 0.94 | -1.29 |
<!-- ORB 30m (baseline) exits: {'eod': 327, 'stop': 83}; rejected: 23652 -->
| ORB 30m + RVOL>=1.0 | +5.50% | 1.55 | 4.68% | 309 | 48.9% | 1.20 | +4.45 |
<!-- ORB 30m + RVOL>=1.0 exits: {'eod': 263, 'stop': 46}; rejected: 5136 -->

## test: 2026-08-04 → 2026-10-09 (48 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +2.19% | 1.27 | 3.66% | 1 | 100.0% | inf | +548.89 |
| ORB 30m (baseline) | -0.91% | -0.71 | 3.28% | 167 | 42.5% | 0.92 | -1.36 |
<!-- ORB 30m (baseline) exits: {'eod': 141, 'stop': 26}; rejected: 8697 -->
| ORB 30m + RVOL>=1.0 | -0.09% | -0.08 | 2.24% | 119 | 44.5% | 0.99 | -0.19 |
<!-- ORB 30m + RVOL>=1.0 exits: {'eod': 98, 'stop': 21}; rejected: 1771 -->
