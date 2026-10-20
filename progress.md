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

---

# Research agents (MAG 7 + AI Sectors) — handoff, updated 2026-10-16

Read-only stock research emails built from Robinhood MCP data. **No orders, ever.** Email goes to
mail11dira@gmail.com only. Branch: `claude/upbeat-knuth-878qp7` (routines fetch it on every run, so a push
changes the next run). PRs: none (not requested).

## Routines (claude.ai scheduled tasks, Mon–Fri, US Central)
| Routine | ID | Schedule | State |
|---|---|---|---|
| MAG 7 Research Agent | `trig_012DY3peEQUikJ9MBxYuLXpG` | `CRON_TZ=America/Chicago 59 7,8 * * 1-5` (7:59, 8:59) | enabled; last run 2026-10-15 OK |
| AI Sectors Research Agent | `trig_01BSEzw8DL1JRFyRSmVnQK6B` | same | **disabled 2026-10-20** (merged into AI Sectors 100) |
| **AI Sectors 100 Research Agent** (was Modern AI Sectors) | `trig_01D3Gr9p5a4cJvwRkuHVThUg` | same | enabled; `--agent ai100`; connectors + repo attached |
| MAG 7 (9:30) | `trig_01TZoDuVzveBgkv4RqgL2pSs` | `29 9 * * 1-5` | **disabled** (old full prompt) |
| AI Sectors (9:30) | `trig_01BRGe391GXt4kzok9eotfwp` | `29 9 * * 1-5` | **disabled** (old full prompt, 59-stock universe) |

- Connectors (Robinhood_Agentic, Gmail) were attached in the claude.ai UI — routines created via MCP get none.
- Times are set 1 min early: minute-0 schedules get re-anchored to the save minute. Minimum interval 1 h.
- MAG 7 routine still has the built-in completion **email notification ON** (user told how to turn it off in UI;
  `update_trigger` cannot change it).
- Cost estimate: MAG 7 ≈ $0.40/run, AI Sectors ≈ $0.50/run after the 32-stock trim (was $0.84) → ≈ $1.80/day.

## How a run works (script-first; prompt in `<agent>/routine_prompt.txt`)
1. Checkout branch → `python3 -m research.plan --agent {mag7|aisectors}` prints the read-only calls.
2. Agent makes all calls in parallel (results land in the session transcript / saved tool-result files).
3. `python3 -m research.report --agent ... --out /tmp/report.html` → JSON {subject, parts (≤24k chars), missing, mode}.
4. Agent `cat`s the parts and sends with `mcp__Gmail__send_message`. Fallback: `routine_prompt_legacy.txt`.
- Local check: `python3 -m research.report --agent mag7 --test --now <ISO> --out <file>` (reads latest transcript),
  `python -m pytest -q` (73 tests).

## Code (`research/`)
`universe.py` (tickers) · `plan.py` (call plan) · `collect.py` (transcript → Dataset) · `ta.py` (indicators) ·
`analyze.py` (per-symbol analysis) · `render.py` (HTML, colors) · `report.py` (MAG 7 / AI Sectors layouts).
Docs per agent: `MAG 7/` and `AI Sectors/` (README, routine prompts, `technical_analysis.md`, sample reports).

## Universes
- **MAG 7:** AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA; benchmarks SPY, QQQ.
- **AI Sectors (32, MAG 7 excluded, each ticker once):** benchmarks SPY, QQQ, SMH, XLU.
  - Memory: L1 ASML AMAT LRCX KLAC · L2 MU SKHY WDC SNDK · L3 TSM · L4 DELL HPE · L5 AVGO AMD
  - AI Power Stack: L1 VST CEG · L3 GEV · L4 CAT VRT · L5 ORCL
  - Data Center: L2 INTC ARM · L3 ANET MRVL CRDO CSCO LITE AAOI
  - Neo-Cloud: L1 CRWV NBIS · L2 IREN CIFR APLD
  - 2026-10-16 trim: kept names with 20-day avg dollar volume ≥ ~$1B; removed 36 (OTC ADRs ASMVY BESIY DSCSY ABBNY;
    UEC LEU AMKR BWXT ENB HUBB ONTO MOD SMR CCJ NVT ASX DLR GNRC NRG CARR OKLO JCI EQIX DUK SO TT NTAP CMI PWR ETN
    TER NEE; n/a Samsung Kioxia PSTG SGRE). Empty layers hidden, layer numbers kept.
  - Neo-cloud runners-up not added: WULF ~$0.43B, CORZ ~$0.20B, GLXY ~$0.12B.

## Technical analysis (both agents, all deterministic in Python)
Volume (time-of-day RVOL, up/down vol, spikes) · VWAP ±1/2σ, slope, reclaim/loss · Levels: PDH/PDL/PDC, PMH/PML,
ORH/ORL, floor pivots, **PWH/PWL, prior-day volume profile POC/VAH/VAL**, 20d & 52w, round numbers · structure,
gap, breaks · 5m EMA 9/21; daily EMA 9/21, SMA 20/50/200, stack, golden/death cross · RSI 14 (5m, daily, divergence)
· ATR 14 (range used, expected range) · **5m MACD 12/26/9, ADX 14 + DI, TTM squeeze** · **inside day / NR7**.
- Bias −6..+6 (vwap, ema, stack, rsi, vol, struct); ≥+3 BULLISH, ≤−3 BEARISH. **Confirmations 0–2** (MACD hist on
  bias side & expanding; ADX ≥ 20 with matching DI).
- Watch levels: merge 0.10 ATR, drop within 0.15 ATR, target ≥ 0.5 ATR (else +0.75 ATR), stop ≥ 0.25 ATR (else 0.5 ATR).
- Top setups: rank |bias| → confirmations → RVOL → R/R; exclude R/R < 1. MAG 7 top 3, AI Sectors top 5.
- Colors: every bullish word/number green (#0a7d2c), bearish red (#c0392b), neutral grey.

- **Modern AI Sectors (94 = 34 ETFs + 60 stocks, 19 sectors; `--agent modern`):** see `Modern AI Sectors/README.md`.
  01 Semis/Memory · 02 AI Infra/Data Centers · 03 Software/Cyber · 04 Power/Grid/Nuclear · 05 Crypto/Fintech ·
  06 Space/Defense · 07 Quantum · 08 Robotics · 09 Real Assets · 10 Economy/Risk · 11 Health/Biotech · 12 Neo-Cloud ·
  13 Leveraged/Volatility · 14 Consumer/Internet · 15 China Tech · 16 Banks/Lending · 17 Travel · 18 Gold & Silver Miners ·
  19 Housing (13-19 added 2026-10-19; INVERSE = SQQQ, SOXS, UVXY excluded from averages/checklist).
  Dedup first listing (IGV, CIBR shown in 03; VRT in 02; PLTR in 03); NVDA, TSLA excluded (MAG 7); PSTG n/a.
  Extra section "Weekend checklist" (new highs, 8/21 hold, 20d outperformance, sector RS, base breakout, volume expansion).
  Screen: ETFs ≥ $150M/day; stocks ≥ $200M/day, price ≥ $5, ATR ≥ 2.5% (`DAYTRADE_REMOVED` in universe.py).
  47 Robinhood calls/run; email ≈ 61 KB (3 parts).

- **AI Sectors 100 (`--agent ai100`, 2026-10-20): THE active sector agent** — merges AI Sectors + Modern AI Sectors into
  the best 100 unique stocks (no ETFs, no MAG 7), 15 sectors, Modern email format. Ranking: screen $200M+/day, px ≥ $5,
  ATR ≥ 2.5%, then avg percentile of $ volume and ATR %; full table in `AI Sectors 100/README.md`. 52 calls/run, ~57 KB.
  AI Sectors and Modern AI Sectors folders are marked retired (code paths still work).

## Change log (this session)
- Built both agents → script-based flow (cost cut) → dropped 9:30 run → watch-level fixes → AI Sectors dedupe/no MAG 7
- 2026-10-16: AI Sectors 59 → 32 stocks + Neo-Cloud ecosystem (c52d8d8, 847ec15)
- 2026-10-16: bullish green / bearish red everywhere (be1a14c)
- 2026-10-16: MACD, ADX/DMI, squeeze, volume profile, PWH/PWL, inside day/NR7, confirmation ranking (7c54987)

- 2026-10-19: new Modern AI Sectors agent; watch-level targets capped at 2 daily ATR for all agents (e07d5dd)

- 2026-10-20: AI Sectors 100 replaces both sector agents; analyst ratings chunked to 75 symbols/call

## Next actions (proceed in the next run)
0a. Check the first AI Sectors 100 run (2026-10-20 7:59 CT) — `trig_01D3Gr9p5a4cJvwRkuHVThUg` last_run.
0. Check the first Modern AI Sectors run (`trig_01D3Gr9p5a4cJvwRkuHVThUg`, 2026-10-19 7:59 CT).
1. Check the first emails with the new indicators (2026-10-16 7:59 and 8:59 CT) — use `list_triggers` for the
   `last_run.session_id`, then `list_events` on it to confirm "sent" and an empty `missing` list.
2. If the user wants a test now: fire the routines (`fire_trigger`) or run the plan + report locally with `--test`.
3. Open decisions for the user: add nuclear names back (CCJ ~$0.30B, OKLO ~$0.37B/day)? turn off the MAG 7
   built-in email notification? delete or update the two disabled 9:30 routines?
4. Optional: refresh the live routines' FALLBACK text to point at `routine_prompt_legacy.txt` (MAG 7 still embeds
   the older indicator list; the script path is unaffected).
