# Graph — Option A: Strategy Research & Backtest

Status: **APPROVED 2026-10-11** — data option (a)

## Nodes

| id | type | input | output | check |
|----|------|-------|--------|-------|
| N0 risk | code | limits in `src/risk.py` | `src/risk.py`, `tests/test_risk.py` | `pytest tests/test_risk.py` passes |
| N1 data | code | saved MCP responses in `data/raw/` | `data/bars_5m.csv.gz` (5-min OHLCV) | no gaps > 1 session, no NaNs, timestamps in US/Eastern, monotonic |
| N2 backtester | code | bars + signal fn + `risk.py` | `src/backtest.py`, `tests/test_backtest.py` | known-answer tests pass; lookahead test (shifted-future signal must not improve results) passes |
| N3 metrics | code | trade list, equity curve | `src/metrics.py`, `tests/test_metrics.py` | Sharpe / max DD / win rate / profit factor match hand-computed fixtures |
| N4 baseline | code | N1, N2, N3 | `backtests/baseline.md` | SPY buy-and-hold + opening-range-breakout (ORB) default params, train & test windows reported |
| N5 strategy | judgment → code | baseline report, learned rules | `src/strategies/<name>.py` | one change vs. previous iteration, documented hypothesis |
| N6 evaluate | code | N5 + N2 + N3 | `backtests/iter_<k>.md` | train tuned only; test evaluated once; costs + slippage on |
| N7 review | judgment | all iter reports | `backtests/report.md` | every claim cites a report file; failed iterations listed |

## Edges
- N1 → N4, N6
- N2 → N4, N6
- N3 → N4, N6
- N0 → N2
- N4 → N5 → N6 → N7
- N6 --(gate fail)--> N5 (correction edge, max 3)
- N6 --(accepted)--> graph.md "Learned rules" (learning edge)

## Parallel groups
- **Wave 1:** N0, N1, N3 (no shared files)
- **Wave 2:** N2 (needs N0)
- **Wave 3:** N4
- **Loop:** N5 → N6 (up to 3 iterations), then N7

## Code nodes (never routed through a model)
N0, N1, N2, N3, N4, N6. Model is used only in N5 (idea) and N7 (write-up).

## Defaults (change before approval if needed)
- Universe: SPY, QQQ, AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA, AMD
- Paper account: $25,000; risk per trade 1%; max position 20% of equity;
  daily loss halt 2%; max 3 open positions; flat by 15:55 ET
- Costs: $0 commission, slippage 0.02% per side
- Windows: train = first 70% of available history, test = last 30%
- Data: Robinhood MCP 5-min historicals → `data/raw/` (gitignored) → `data/bars_5m.csv.gz`

## Data decision (resolved: option a)
- yfinance is blocked by this environment's network policy; Robinhood MCP is the only source.
- Robinhood intraday bars before ~2026-02-23 are interpolated filler (all intervals), so real
  history is ~160 sessions. 5-minute bars cover the same window, so we use 5-minute bars.
- Fetch limits: 5,000 bars per request and one symbol per request (multi-symbol responses overflow).
- Train = first 112 sessions (2026-02-23 → ~2026-08-03), test = last 48 sessions.

## Learned rules
_(none yet — only added after an out-of-sample pass)_

### Run 1 observations (not rules — failed the out-of-sample gate)
- Relative-volume filter (RVOL ≥ 1.0) improved ORB in both train and test; worth retesting on more data.
- Long-only ORB is regime-fitting: train Sharpe 1.23 → test -2.96.
- With ~160 sessions, train-window improvements are not trustworthy on their own.
