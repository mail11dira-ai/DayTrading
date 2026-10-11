# Progress

## Graph
- **Done:** N0 risk, N1 data, N2 backtester, N3 metrics, N4 baseline, N5/N6 × 3 iterations, N7 report
- **Running:** —
- **Blocked:** none. Run 1 ended at its limit of 3 iterations; **no strategy passed the out-of-sample gate.**

## Outputs
- Code: `src/risk.py`, `src/data.py`, `src/backtest.py`, `src/metrics.py`, `src/evaluate.py`,
  `src/iterations.py`, `src/strategies/orb.py` — 48 tests pass (`python -m pytest -q`)
- Data: `data/bars_5m.csv.gz` (raw MCP JSON in `data/raw/`, gitignored)
- Reports: `backtests/baseline.md`, `backtests/iter_1.md`, `iter_2.md`, `iter_3.md`, `backtests/report.md`

## Decisions
- 2026-10-11: Graph approved; data option (a). yfinance blocked by network policy → Robinhood MCP only.
- Real intraday history starts 2026-02-23 (earlier bars are interpolated) → 160 sessions, 5-min bars.
- Train/test = 112/48 sessions. Test evaluated exactly once per iteration.
- iter_1 (long-only) rejected: overfit. iter_2 (60m range) rejected. iter_3 (RVOL ≥ 1.0) rejected
  vs. SPY but the best candidate; recorded as an observation in `graph.md`, not a rule.

## Open issues
- Short single-regime history (biggest limitation).
- Alphabetical priority when the 3-position cap binds (fix in N2: rank signals).
- Push to GitHub fails with 403 (Claude GitHub App lacks access to the repo).

## Next action
User decision: add a multi-year intraday data source, then run 2 = capacity-bias fix + walk-forward
retest of the RVOL filter.
