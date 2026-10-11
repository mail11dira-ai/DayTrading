# iter_2

**Change:** opening range 60 min (`range_bars=12`) vs. baseline 30 min. iter_1 (long-only) was rejected, so this changes the baseline, not iter_1.

**Hypothesis:** a longer range filters false breakouts.

**Train-only tuning** (test untouched): 15m Sharpe -1.85, 30m -0.48, 60m -0.04, 90m -0.89. 60m chosen.

Config: $25,000 start, slippage 0.02%/side, $0 commission, risk limits from `src/risk.py` defaults.

## train: 2026-02-23 → 2026-08-03 (112 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +9.90% | 1.54 | 9.23% | 1 | 100.0% | inf | +2480.26 |
| ORB 30m (baseline) | -2.12% | -0.48 | 7.18% | 410 | 47.3% | 0.94 | -1.29 |
<!-- ORB 30m (baseline) exits: {'eod': 327, 'stop': 83}; rejected: 23652 -->
| ORB 60m | -0.29% | -0.04 | 5.08% | 382 | 46.9% | 0.99 | -0.19 |
<!-- ORB 60m exits: {'eod': 331, 'stop': 51}; rejected: 15954 -->

## test: 2026-08-04 → 2026-10-09 (48 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +2.19% | 1.27 | 3.66% | 1 | 100.0% | inf | +548.89 |
| ORB 30m (baseline) | -0.91% | -0.71 | 3.28% | 167 | 42.5% | 0.92 | -1.36 |
<!-- ORB 30m (baseline) exits: {'eod': 141, 'stop': 26}; rejected: 8697 -->
| ORB 60m | -1.46% | -1.77 | 3.44% | 161 | 44.7% | 0.84 | -2.26 |
<!-- ORB 60m exits: {'eod': 142, 'stop': 19}; rejected: 4454 -->
