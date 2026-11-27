# iter_4

**Change:** new strategy family, VWAP reclaim (`src/strategies/vwap.py`): 5-min close crosses session VWAP after 10:00 ET with cumulative relative volume >= threshold; stop at the last 6 bars' extreme, target 2R. Compared with ORB baseline and the iter_3 volume filter.

**Hypothesis:** VWAP reclaims on participation show trend resumption better than opening-range breaks.

**Train-only tuning** (test untouched): rvol >= 1.0 Sharpe 1.57, 1.5 -> -0.21, 2.0 -> 0.53. 1.0 chosen (the same threshold as iter_3). Note: this is one of 3 threshold trials on train.

Config: $25,000 start, slippage 0.02%/side, $0 commission, risk limits from `src/risk.py` defaults.

## train: 2026-02-23 → 2026-08-03 (112 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +9.90% | 1.54 | 9.23% | 1 | 100.0% | inf | +2480.26 |
| ORB 30m (baseline) | -2.12% | -0.48 | 7.18% | 410 | 47.3% | 0.94 | -1.29 |
<!-- ORB 30m (baseline) exits: {'eod': 327, 'stop': 83}; rejected: 23652 -->
| ORB 30m + RVOL>=1.0 | +5.50% | 1.55 | 4.68% | 309 | 48.9% | 1.20 | +4.45 |
<!-- ORB 30m + RVOL>=1.0 exits: {'eod': 263, 'stop': 46}; rejected: 5136 -->
| VWAP reclaim + RVOL>=1.0 | +3.91% | 1.57 | 3.31% | 336 | 45.5% | 1.18 | +2.91 |
<!-- VWAP reclaim + RVOL>=1.0 exits: {'stop': 134, 'eod': 130, 'target': 72}; rejected: 241 -->

## test: 2026-08-04 → 2026-10-09 (48 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +2.19% | 1.27 | 3.66% | 1 | 100.0% | inf | +548.89 |
| ORB 30m (baseline) | -0.91% | -0.71 | 3.28% | 167 | 42.5% | 0.92 | -1.36 |
<!-- ORB 30m (baseline) exits: {'eod': 141, 'stop': 26}; rejected: 8697 -->
| ORB 30m + RVOL>=1.0 | -0.09% | -0.08 | 2.24% | 119 | 44.5% | 0.99 | -0.19 |
<!-- ORB 30m + RVOL>=1.0 exits: {'eod': 98, 'stop': 21}; rejected: 1771 -->
| VWAP reclaim + RVOL>=1.0 | -3.89% | -5.83 | 4.25% | 130 | 36.2% | 0.54 | -7.48 |
<!-- VWAP reclaim + RVOL>=1.0 exits: {'stop': 64, 'eod': 48, 'target': 18}; rejected: 72 -->
