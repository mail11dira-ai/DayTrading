# iter_5

**Change:** market-regime filter on the best prior candidate (ORB 30m + RVOL>=1.0). Longs only when SPY's previous close is above its 20-day average; shorts only when below (`src/strategies/regime.py`).

**Hypothesis:** breakouts fail against the broad trend; trading only with SPY should cut the losing counter-trend trades that dominated run 1.

**Tuning:** none. The 20-day window was fixed before running, to avoid tuning on either window.

Config: $25,000 start, slippage 0.02%/side, $0 commission, risk limits from `src/risk.py` defaults.

## train: 2026-02-23 → 2026-08-03 (112 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +9.90% | 1.54 | 9.23% | 1 | 100.0% | inf | +2480.26 |
| ORB 30m + RVOL>=1.0 | +5.50% | 1.55 | 4.68% | 309 | 48.9% | 1.20 | +4.45 |
<!-- ORB 30m + RVOL>=1.0 exits: {'eod': 263, 'stop': 46}; rejected: 5136 -->
| ORB 30m + RVOL>=1.0 + SPY regime | +8.47% | 2.94 | 3.38% | 191 | 54.5% | 1.58 | +11.08 |
<!-- ORB 30m + RVOL>=1.0 + SPY regime exits: {'eod': 171, 'stop': 20}; rejected: 2102 -->

## test: 2026-08-04 → 2026-10-09 (48 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +2.19% | 1.27 | 3.66% | 1 | 100.0% | inf | +548.89 |
| ORB 30m + RVOL>=1.0 | -0.09% | -0.08 | 2.24% | 119 | 44.5% | 0.99 | -0.19 |
<!-- ORB 30m + RVOL>=1.0 exits: {'eod': 98, 'stop': 21}; rejected: 1771 -->
| ORB 30m + RVOL>=1.0 + SPY regime | +0.85% | 1.59 | 1.09% | 66 | 42.4% | 1.26 | +3.21 |
<!-- ORB 30m + RVOL>=1.0 + SPY regime exits: {'eod': 53, 'stop': 13}; rejected: 386 -->
