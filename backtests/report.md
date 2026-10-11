# Report — Run 1 (Option A: research & backtest)

**Status: partial — run limit reached (3/3 iterations). No strategy passed the out-of-sample gate.**
No rule was promoted to `graph.md` "Learned rules".

## Setup
- Data: Robinhood 5-minute bars, regular hours, 10 symbols (SPY QQQ AAPL MSFT NVDA AMZN META GOOGL TSLA AMD),
  2026-02-23 → 2026-10-09, 160 sessions, 124,800 bars, validated (`checks.md` N1).
  Earlier Robinhood intraday bars are interpolated filler, so this is all the real history available.
- Split by whole sessions: train 112 (→ 2026-08-03), test 48 (2026-08-04 → 2026-10-09).
- Engine: `src/backtest.py` — next-bar-open fills, intrabar stops (stop wins ties), flat by 15:55,
  0.02% slippage per side, every entry sized and gated by `src/risk.py` ($25k, 1% risk, 20% max
  position, 2% daily loss halt, 3 max positions).
- Gate: out-of-sample (test) must beat the baseline, max drawdown < 10%, costs on.

## Results (test window, evaluated once per iteration)

| run | change vs. baseline | train Sharpe | test return | test Sharpe | test max DD | verdict | evidence |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | — | 1.54 | +2.19% | 1.27 | 3.66% | baseline | `backtests/baseline.md` |
| ORB 30m | — | -0.48 | -0.91% | -0.71 | 3.28% | baseline | `backtests/baseline.md` |
| iter_1 long-only | no shorts | 1.23 | -3.25% | -2.96 | 4.57% | **fail** — overfit to rising market | `backtests/iter_1.md` |
| iter_2 ORB 60m | 60-min range | -0.04 | -1.46% | -1.77 | 3.44% | **fail** | `backtests/iter_2.md` |
| iter_3 RVOL ≥ 1.0 | volume filter | 1.55 | -0.09% | -0.08 | 2.24% | **fail** — beats ORB, not SPY | `backtests/iter_3.md` |

## What we learned (observations, not proven rules)
1. **Train-window wins don't transfer.** Two of three changes improved train Sharpe by ~1.7–2.0 and
   then did worse or only break-even on test. With 112 train sessions in one market regime, a
   good train result alone means little.
2. **Relative volume is the only change that helped in both windows** (train -0.48 → 1.55, test
   -0.71 → -0.08, drawdown down in both). The warm-up confound was ruled out. It's still not
   profitable out-of-sample, and 119 test trades are far too few to call it significant.
3. **Long-only is regime-fitting.** It worked while the market rose (train) and failed when the
   test window chopped.

## Known limitations
- **Short history:** 160 sessions in one regime. This is the biggest limitation, ahead of anything in the code.
- **Capacity bias:** with a 3-position cap, simultaneous signals fill in alphabetical order
  (≈22k signals rejected on train for max positions), so AAPL/AMD/AMZN get priority.
- RVOL warm-up costs the first 10 sessions of each window (test traded 38 of 48 sessions).
- Slippage is a flat 0.02%; there's no spread or market-impact model. No commissions (Robinhood).
- No significance testing (bootstrap or permutation) yet.

## Recommended next run (needs your decision)
1. **More data first.** Add a paid intraday source (Polygon/Alpaca/Databento, multi-year) so results
   cover several regimes. Every other improvement depends on this.
2. Fix the capacity bias: rank simultaneous signals by RVOL instead of alphabetically (a backtester change, N2).
3. Re-test the RVOL filter with walk-forward windows and a bootstrap confidence interval.
4. Keep live trading off. Nothing here justifies risking money.
