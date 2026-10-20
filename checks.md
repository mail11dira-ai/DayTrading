# Checks

Completion checklist (Option A). Each item must point to observable evidence.

| node | requirement | verdict | evidence |
|------|-------------|---------|----------|
| N0 | Position sizing caps risk at 1% of equity | pass | `pytest tests/test_risk.py` — 9 tests / 12 cases passed |
| N0 | Position size capped at 20% of equity | pass | `tests/test_risk.py::test_position_cap` |
| N0 | Daily loss halt at 2% blocks new trades | pass | `tests/test_risk.py::test_daily_loss_halt` |
| N0 | Max open positions and end-of-day cutoff enforced | pass | `tests/test_risk.py::test_max_open_positions`, `::test_eod_cutoff` |
| N1 | Cached bars complete, clean, tz-aware | pass | `python -m src.data data/raw data/bars_5m.csv.gz` → VALIDATION: pass; 10 symbols × 160 sessions × 78 bars = 124,800 rows (2026-02-23 → 2026-10-09); `tests/test_data.py` 5 passed |
| N2 | Backtester passes known-answer and lookahead tests | pass | `tests/test_backtest.py` 10 passed (incl. `test_strategy_never_sees_future_bars`, `test_truncation_invariance`) |
| N3 | Metrics match hand-computed fixtures | pass | `tests/test_metrics.py` 18 passed (full suite 35 passed) |
| N4 | Baseline reported on train and test windows | pass | `backtests/baseline.md` |
| N6 iter_1 | Long-only beats baseline out-of-sample | fail | test Sharpe -2.96 vs ORB -0.71, SPY 1.27 — `backtests/iter_1.md` |
| N6 iter_2 | ORB 60m beats baseline out-of-sample | fail | test Sharpe -1.77 — `backtests/iter_2.md` |
| N6 iter_3 | ORB + RVOL≥1.0 beats baseline out-of-sample | fail | test -0.09% / Sharpe -0.08: beats ORB (-0.71), not SPY (1.27); max DD 2.24% — `backtests/iter_3.md` |
| N7 | Report cites evidence; failed iterations listed | pass | `backtests/report.md` |
| all | Order-placing tools blocked | pass | `.claude/settings.json` deny list |
| all | Full test suite | pass | `python -m pytest -q` → 48 passed |
| research agents | bias score (>= +3 / <= -3) predicts the next 60-min market-adjusted return (65 sessions, 8:59 CT, no look-ahead) | fail | backtests/bias_validation.md (spread -0.13%/day, t = -1.2; top-5 ranking -0.06%/day, t = -0.6; no signal supported) |
| research agents | every bias component can change the score at 8:59 CT | fail | backtests/bias_validation.md section 0: intraday structure is neutral on 99% of stock-days |
| research agents | decision on the failed bias-score gate (2026-10-20) | unresolved | user chose to keep the score as a descriptive chart-state summary; emails carry the validation note; the two fail rows above stand. Re-test with `python -m research.validate` after ~60 more sessions |
| research agents | full test suite after review pass (breadth regime, validation note, expected range) | pass | `python -m pytest -q` → 87 passed |
| research agents | ad-hoc end-to-end runs, 2026-10-20 00:28 / 00:31 CT | pass | `research.report --test`: MAG 7 and AI Sectors 100 both `missing: []`, 25 KB / 27 KB; sent to mail11dira@gmail.com |
