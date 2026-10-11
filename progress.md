# Progress

## Graph
- **Done:** N0 risk (12/12 tests pass)
- **Running:** —
- **Blocked:** N1–N7 waiting on approval of `graph.md` (layer 1 pause)

## Outputs
- `src/risk.py`, `tests/test_risk.py`
- `.claude/settings.json` — order/cancel/exercise tools denied

## Decisions
- 2026-10-11: Option A (research & backtest only). Defaults: $25k paper equity, 1% risk/trade,
  20% max position, 2% daily loss halt, 3 max open positions, flat by 15:55 ET.
- Risk module built first so the backtester (N2) depends on it from day one.

## Open issues
- Intraday data history length (see "Open question" in `graph.md`).

## Next action
Approve or edit `graph.md`, then run Wave 1: N1 data + N3 metrics (parallel).
