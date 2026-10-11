# Checks

Completion checklist (Option A). Each item must point to observable evidence.

| node | requirement | verdict | evidence |
|------|-------------|---------|----------|
| N0 | Position sizing caps risk at 1% of equity | pass | `pytest tests/test_risk.py` — 9 tests / 12 cases passed |
| N0 | Position size capped at 20% of equity | pass | `tests/test_risk.py::test_position_cap` |
| N0 | Daily loss halt at 2% blocks new trades | pass | `tests/test_risk.py::test_daily_loss_halt` |
| N0 | Max open positions and end-of-day cutoff enforced | pass | `tests/test_risk.py::test_max_open_positions`, `::test_eod_cutoff` |
| N1 | Cached bars complete, clean, tz-aware | pass | `python -m src.data data/raw data/bars_5m.csv.gz` → VALIDATION: pass; 10 symbols × 160 sessions × 78 bars = 124,800 rows (2026-02-23 → 2026-10-09); `tests/test_data.py` 5 passed |
| N2 | Backtester passes known-answer and lookahead tests | unresolved | not started |
| N3 | Metrics match hand-computed fixtures | pass | `tests/test_metrics.py` 18 passed (full suite 35 passed) |
| N4 | Baseline reported on train and test windows | unresolved | not started |
| N6 | Strategy beats baseline out-of-sample, max DD < 10%, costs on | unresolved | not started |
| N7 | Report cites evidence; failed iterations listed | unresolved | not started |
| all | Order-placing tools blocked | pass | `.claude/settings.json` deny list |
