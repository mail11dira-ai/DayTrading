# DayTrading — Agent Graph Instructions

This repo builds and backtests a day-trading strategy as a **graph of bounded nodes**
(adapted from the Karpathy-inspired graph prompt). Phase: **Option A — research & backtest only.
No live orders.**

## Goal
Complete the task in `graph.md` as a graph of bounded nodes, not one long session.
Leave a usable result, a verification report (`checks.md`), and `graph.md` so another
session can rerun or extend it. Stop when every node's checks pass or the run limit is reached.

## Inputs
- **Task:** Build and backtest an intraday momentum strategy on liquid US large caps.
- **Output:** `src/` (strategy + backtester), `backtests/report.md`, `data/` (cached bars).
- **Acceptance checks:** see `checks.md` (out-of-sample beats baseline, max drawdown < 10%,
  no lookahead, all risk rules unit-tested, costs/slippage included).
- **Sources:** Robinhood MCP read-only tools (historicals, quotes, earnings calendar);
  public data via `yfinance` as a fallback for longer history.
- **Scope:** this repo only. Never call order-placing tools (blocked in `.claude/settings.json`).
- **Run limit:** 3 strategy iterations per run, or stop and report.

## Principles
- Establish a baseline before changing the system (buy-and-hold SPY + simple rule strategy).
- Every node has one clear scope and a fixed evaluator.
- Change one thing, measure it, keep useful improvements. Record failed attempts too.
- Prefer fewer nodes when results are comparable.
- **Out-of-sample or it didn't happen.** Parameters are tuned on the train window only;
  the test window is evaluated once per iteration.

## Hard rules
1. **Code, not model, for anything deterministic:** indicators, signals, position sizing,
   risk limits, P&L, metrics. Model calls are for judgment only (strategy ideas, reviewing results).
2. **All sizing and limits go through `src/risk.py`.** Never bypass or loosen it to get a pass.
3. **Never weaken a gate or check to obtain a pass.** Report the failure instead.
4. Two nodes never edit the same file.
5. Ask before publishing, sending, or spending anything. No order placement in this phase.

## Gates & return paths
- Gate order: deterministic checks (tests, metrics) → node report → model confidence last.
- Record each verdict in `checks.md`: `node | requirement | verdict | evidence`
  (verdict = pass / fail / unresolved; evidence = file path or actual command output).
- **Correction edge:** a failed gate returns to the node that made it, with the reason,
  the evidence and scope "fix this node only". Max 3 attempts, then mark blocked.
- **Learning edge:** after an accepted result, write the proven rule into `graph.md`
  under "Learned rules" — only if it held out-of-sample.

## Execution loop
1. Read `graph.md` and `progress.md`; pick the next ready nodes.
2. Run independent nodes in parallel (subagents with only the context they need).
3. Pass every output through its gate.
4. Return failed units, never the whole batch.
5. Merge accepted outputs.
6. Continue until completion, a blocker, or the run limit.

## Handoff
After each stage update `progress.md` (nodes done/running/blocked, output paths,
decisions, open issues, next action). On resumption read `graph.md` and `progress.md` first.

## Commands
- Tests: `python -m pytest -q`
- Deps: `pip install -r requirements.txt`
