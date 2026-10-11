# iter_1

**Change:** long-only (`allow_short=False`) vs. baseline ORB.

**Hypothesis:** in the train window longs made +$1,200 and shorts lost -$1,730 (410 trades); downside breakouts in a rising market are mostly noise.

Config: $25,000 start, slippage 0.02%/side, $0 commission, risk limits from `src/risk.py` defaults.

## train: 2026-02-23 → 2026-08-03 (112 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +9.90% | 1.54 | 9.23% | 1 | 100.0% | inf | +2480.26 |
| ORB 30m (baseline) | -2.12% | -0.48 | 7.18% | 410 | 47.3% | 0.94 | -1.29 |
<!-- ORB 30m (baseline) exits: {'eod': 327, 'stop': 83}; rejected: 23652 -->
| ORB 30m long-only | +4.35% | 1.23 | 5.77% | 329 | 49.8% | 1.17 | +3.30 |
<!-- ORB 30m long-only exits: {'eod': 266, 'stop': 63}; rejected: 9951 -->

## test: 2026-08-04 → 2026-10-09 (48 sessions)

| run | total return | Sharpe | max DD | trades | win rate | profit factor | avg trade $ |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +2.19% | 1.27 | 3.66% | 1 | 100.0% | inf | +548.89 |
| ORB 30m (baseline) | -0.91% | -0.71 | 3.28% | 167 | 42.5% | 0.92 | -1.36 |
<!-- ORB 30m (baseline) exits: {'eod': 141, 'stop': 26}; rejected: 8697 -->
| ORB 30m long-only | -3.25% | -2.96 | 4.57% | 143 | 37.1% | 0.71 | -5.68 |
<!-- ORB 30m long-only exits: {'eod': 119, 'stop': 24}; rejected: 3155 -->
