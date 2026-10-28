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
- Colors (2026-10-20 rule, `render.words_only`): ONLY the words Bullish (green #0a7d2c) and Bearish (red #c0392b) are coloured; numbers, up/down words, row tints and card borders are uncoloured; bias pills are coloured only when they say BULLISH/BEARISH. Look & feel (2026-10-20): dark header
  bar + legend, tinted bias pills (BULLISH green / BEARISH red / NEUTRAL grey), rows shaded green/red (ticker tables by bias,
  sector scoreboard by day move), cards with a green/red left border, dark table headers. All in `render.py` STYLE (class-based, ~2 KB).

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
  ATR ≥ 2.5%, then avg percentile of $ volume and ATR %; full table in `AI Sectors 100/README.md`. 52 calls/run;
  compact email since 2026-10-20 (~24 KB, 1 part: snapshot, scoreboard, checklist, top 5, risks - no per-sector tables).
  AI Sectors and Modern AI Sectors folders are marked retired (code paths still work).

- **New signals (2026-10-20, both agents):** volume-confirmed opening-range breakout (ORB), pre-market RVOL + gap quality,
  intraday RS vs QQQ (15/30 min), breadth/regime + VIX. One extended-hours 5-min pull per symbol (AI Sectors 100: 42 calls/run,
  MAG 7: 7). Plan includes `get_index_quotes` for VIX (id `3b912aa2-88f9-4682-8ae3-e39520bdf4db`); both live routine prompts load that tool.
- **Bias-score validation (`python3 -m research.validate`, report `backtests/bias_validation.md`, samples
  `backtests/bias_validation_samples.json.gz`; regenerate with `--from-samples`):** 65 sessions x 100 stocks at 09:00 CT, market-adjusted,
  no look-ahead. **No signal predicts the next hour**: headline bias spread -0.13%/day (t -1.2), top-5 ranking -0.06%/day (t -0.6),
  ORB / RS / MACD-ADX confirmations all no clear edge; "holding 8/21" weakly inverted (t -2.2, plausible chance among 12 tests).
  Control passes (score describes the trailing 30-min move, t +26). **Intraday-structure component is dead at 8:59** (neutral 99%).
  Emails now carry a one-line note that the score is descriptive. Pre-market/gap signals could not be tested (no past pre-market history).

## Change log (this session)
- Built both agents → script-based flow (cost cut) → dropped 9:30 run → watch-level fixes → AI Sectors dedupe/no MAG 7
- 2026-10-16: AI Sectors 59 → 32 stocks + Neo-Cloud ecosystem (c52d8d8, 847ec15)
- 2026-10-16: bullish green / bearish red everywhere (be1a14c)
- 2026-10-16: MACD, ADX/DMI, squeeze, volume profile, PWH/PWL, inside day/NR7, confirmation ranking (7c54987)

- 2026-10-19: new Modern AI Sectors agent; watch-level targets capped at 2 daily ATR for all agents (e07d5dd)

- 2026-10-20: AI Sectors 100 replaces both sector agents; analyst ratings chunked to 75 symbols/call
- 2026-10-20: AI Sectors 100 email made compact (57 KB -> 24 KB). MAG 7 built-in notification: user turns it off in the UI
- 2026-10-20 (review pass + ad-hoc [TEST] runs of both agents, sent 00:28/00:31 CT, missing = [] for both):
  breadth regime now scored on % up + % above VWAP only (holding 8/21 shown, not scored - it was non-predictive and
  dragged the label to RISK-OFF on up days); validation note names the universe tested (AI Sectors 100);
  "expected range left" says "none (full ATR used)" instead of a zero-width range.

- 2026-10-21: Gmail strips <style>, classes and backgrounds -> all email styles inlined (render.inline), dark text instead of
  white-on-dark. Indicator review (backtests/indicator_review.md, research/indicator_review.py): no direction indicator
  works at 8:59 CT; movement flags do -> added in-play score 0-4 (cards, "Most in play" list, top-setup ranking first);
  removed squeeze-fired / inside-NR7 / divergence risk lists and the "range used > 1" exhaustion line; bias unchanged.
- 2026-10-21: cost cut (user chose "slim the emails" only): cards trimmed to 10 lines, ADX column -> in-play score,
  no <style>/class markup in the sent email. MAG 7 34 KB -> 20 KB, AI Sectors 100 35 KB -> 21 KB, one part each.
  Not applied (offered): drop AI100 quote/ratings calls, one run per day, Haiku model.
- 2026-10-23: MAG 7 section 1 is now a market deep dive (research/market.py): QQQ vs SPY, VIX level/change/regime/
  20-day + 1-year context and intraday path, SPY/QQQ VIX-implied move bands with measured reliability (SPY closed inside
  the band 85% of the last 250 days), full SPY/QQQ cards with index levels. +2 VIX history calls (mag7 only; tool added
  to the live MAG 7 prompt). Email ~20 KB -> ~27 KB.
- 2026-10-26: schedule changed to 8:30 + 8:59 CT (Mon-Fri). The scheduler needs >= 1 hour between runs of one task, so each
  agent now has two tasks: 8:59 = trig_012DY3peEQUikJ9MBxYuLXpG (MAG 7) / trig_01D3Gr9p5a4cJvwRkuHVThUg (AI100);
  8:30 = trig_01TZoDuVzveBgkv4RqgL2pSs (MAG 7, old 9:30 task, has connectors but NO repo attached) /
  trig_01BSEzw8DL1JRFyRSmVnQK6B (AI100, old AI Sectors task, has connectors + repo). Cloning the repo in a run does not
  work: the session blocks running downloaded code, so the MAG 7 8:30 task falls back to the model-built report until
  the user attaches mail11dira-ai/DayTrading to it in the Claude app. trig_01BRGe391GXt4kzok9eotfwp disabled (spare).
  Server staggers the 8:30 start by a few minutes (~8:33-8:38 CT).
- 2026-10-27: MAG 7 agent renamed Super 100 (agent key `super100`, research/universe.py SUPER100): the user's 99-stock
  list in 13 sectors, incl. the MAG 7, no day-trading screen, BRK.B. AI Sectors 100 layout + the SPY/QQQ/VIX deep dive.
  44 calls/run (MAG 7 had 9). Live check 2026-10-27 00:55 CT: 26,992 B, missing []. Both former MAG 7 tasks now run
  `--agent super100`. The `mag7` code path is kept for history.

## Next actions (proceed in the next run)
Build status: COMPLETE (2026-10-20). Both agents (MAG 7, AI Sectors 100) are live, Mon-Fri 7:59 and 8:59 CT.
Decision (user, 2026-10-20): keep the bias score as-is, as a descriptive chart-state summary (no re-weighting,
structure component left unchanged). The validation fail rows in checks.md stand; the email note says so.
1. Check the first live runs with this build (2026-10-20 7:59 / 8:59 CT): `list_triggers` -> `last_run.session_id`,
   then `list_events` to confirm "sent" and an empty `missing` list.
2. MAG 7 built-in email notification is still ON (UI-only setting; the user turns it off).
3. Maintenance only: re-run `python -m research.validate` and `python -m research.indicator_review` after ~60 more sessions (held-out period) before any
   change to the bias score. Never tune on the same 65 sessions.
4. Optional: refresh the live routines' FALLBACK text to point at `routine_prompt_legacy.txt`.
- 2026-10-27: Super 100 now 100 stocks - SPCX added (user request) to 11 Industrials & Defense. SPCX: active, real daily bars
  since 2026-06-12 (93 sessions), ~111M shares/day. Plan still 44 calls. Both Super 100 scheduled tasks' fallback lists updated.
- 2026-10-27: ONE agent only (user request): Super 100 runs Mon-Fri 8:15 CT (pre-market mode, trig_01BSEzw8DL1JRFyRSmVnQK6B -
  the former AI100 8:30 task, repo attached) and 9:01 CT (trig_012DY3peEQUikJ9MBxYuLXpG, repo attached; 30-min window
  complete at 9:00). Disabled, not deleted: AI Sectors 100 8:59 (trig_01D3Gr9p5a4cJvwRkuHVThUg, prompt intact) and
  Super 100 8:30 no-repo (trig_01TZoDuVzveBgkv4RqgL2pSs). Spare trig_01BRGe391GXt4kzok9eotfwp still disabled.
  Cost ~ $1.70/day (~$37/month) vs ~$3.35/day before. AI100 code and tests kept, so it can be re-enabled.
- 2026-10-27 cost cuts (user approved 1,2,3,5): Super 100 scheduled tasks (8:15 and 9:01 CT) now run claude-haiku-5-5.
  plan.py: 5-minute history calls batched 5 -> 10 symbols (super100 plan 44 -> 34 calls). report.py/render.py: super100
  email drops the weekend checklist, shows 3 setups with short cards (render.card brief=True); synthetic build 25.0 -> 19.5 KB
  (not the ~10 KB estimated before). The 9:01 "send a notification email on finish" setting cannot be changed by the
  scheduler API - set it in the task UI. Tests: 97 passed.
- 2026-10-27 AI Sectors 100 back on, two runs Mon-Fri CT: 8:45 (trig_01D3Gr9p5a4cJvwRkuHVThUg, repo attached) and
  1:30 pm (trig_01BRGe391GXt4kzok9eotfwp, no repo: its prompt clones the public repo at run time, which may be blocked).
  Both on claude-haiku-5-5. Code: ai100 skips analyst ratings (plan 32 -> 30 calls); ai100 email is short like super100
  (no weekend checklist, 3 setups, short cards; synthetic build 14.6 KB). Option 5 (shorter 400-day daily history) NOT
  applied: the 52-week high/low use 252 sessions, so it would change the numbers; the saving is about 5%.
- 2026-10-28 AI Sectors 100 universe replaced with the top-100 list (user request) from the 10-27 close ranking
  (SNPS, TXN, ... FSLR; 16 sectors, research/universe.py AI100, USER_LISTS now includes ai100: no day-trade screen,
  no MODERN notes). Email/plan unchanged; ai100 plan 30 calls. Routine prompt fallback lists still show the old
  universe (used only if the repo script fails). Tests: 97 passed.
- 2026-10-28 AI Sectors 100: runs moved to 9:00 and 10:00 CT (trig_01D3Gr9p5a4cJvwRkuHVThUg and trig_01BRGe391GXt4kzok9eotfwp);
  email shows top 7 setups (report.py: ai100 -> 7; Super 100 unchanged at 3). Tests: 97 passed.
- 2026-10-28 AI Sectors 100 day-trading cleanup (user request, scope: this agent only, bias formula unchanged):
  removed from the email: 20-day RS column, 8/21 holding column and breadth line, daily RSI in the RSI risk list.
  Kept: 5m EMA/RSI, VWAP, PDH/PDL/PDC, PMH/PML, ORB, gap, RVOL, daily ATR (range unit), in-play, bias, confirmations.
  Not added: no new indicators; the review found no validated direction edge to add (see backtests/indicator_review.md).
- 2026-10-28 Super 100 universe replaced with the user's list only: GOOGL, AAPL, MSFT, META, AMZN, NVDA, AVGO, AMD,
  VRT, CRWD, TSLA, SPCX (12 unique; the request had 11 numbered items plus GOOGL). research/universe.py SUPER100, README,
  test updated. Tests: 97 passed.
- 2026-10-28 Super 100 runs moved to 8:45 and 9:45 CT (trig_01BSEzw8DL1JRFyRSmVnQK6B, trig_012DY3peEQUikJ9MBxYuLXpG);
  email shows up to 7 setups (report.py: super100 -> 7; only setups with bias and R/R >= 1 qualify). Tests: 97 passed.
