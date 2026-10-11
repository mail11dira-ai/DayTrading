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
