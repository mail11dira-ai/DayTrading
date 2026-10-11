# Baseline



Config: $25,000 start, slippage 0.02%/side, $0 commission, risk limits from `src/risk.py` defaults.

## train: 2026-02-23 → 2026-08-03 (112 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +9.90% | 1.54 | 9.23% | 1 | 100.0% | inf | +2480.26 |
| ORB 30m (default) | -2.12% | -0.48 | 7.18% | 410 | 47.3% | 0.94 | -1.29 |
<!-- ORB 30m (default) exits: {'eod': 327, 'stop': 83}; rejected: 23652 -->

## test: 2026-08-04 → 2026-10-09 (48 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +2.19% | 1.27 | 3.66% | 1 | 100.0% | inf | +548.89 |
| ORB 30m (default) | -0.91% | -0.71 | 3.28% | 167 | 42.5% | 0.92 | -1.36 |
<!-- ORB 30m (default) exits: {'eod': 141, 'stop': 26}; rejected: 8697 -->
