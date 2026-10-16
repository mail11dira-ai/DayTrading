# AI Sectors — Stock Research Agent

An hourly, research-only report on AI-sector stocks, built from Robinhood data and emailed to
mail11dira@gmail.com. Same setup as `../MAG 7`. **No orders are ever placed.**

## What it does
- **Universe: 4 ecosystems — 32 liquid stocks.** Each ticker is listed once, and the MAG 7 (AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA) are excluded because the MAG 7 agent covers them.

  **1. Memory Ecosystem**
  | Layer | Sector | Tickers |
  |---|---|---|
  | 1 | Equipment | ASML, AMAT, LRCX, KLAC |
  | 2 | Memory Makers | MU, SK Hynix (SKHY), WDC, SNDK |
  | 3 | Packaging & Test | TSM |
  | 4 | Storage Platforms | DELL, HPE |
  | 5 | AI Demand | AVGO, AMD |

  **2. AI Power Stack**
  | Layer | Sector | Tickers |
  |---|---|---|
  | 1 | Generation | VST, CEG |
  | 3 | Grid | GEV |
  | 4 | Power Management | CAT, VRT |
  | 5 | Demand Centers | ORCL |

  **3. Data Center Ecosystem**
  | Layer | Sector | Tickers |
  |---|---|---|
  | 2 | Compute | INTC, ARM |
  | 3 | Networking | ANET, MRVL, CRDO, CSCO, LITE, AAOI |

  **4. Neo-Cloud Ecosystem** (added 2026-10-16: top 5 neo-clouds by 20-day avg dollar volume)
  | Layer | Sector | Tickers |
  |---|---|---|
  | 1 | GPU Clouds | CRWV (CoreWeave ~$2.9B/day), NBIS (Nebius ~$3.9B/day) |
  | 2 | AI Hosting / HPC | IREN (~$1.7B/day), CIFR (~$0.6B/day), APLD (~$0.6B/day) |

  Next by volume (not added): WULF ~$0.43B, CORZ ~$0.20B, GLXY ~$0.12B.

  **Trim (2026-10-16):** stocks with 20-day average dollar volume below ~$1B were removed, plus the 4
  names not on Robinhood. 36 removed: ASMVY, BESIY, DSCSY, ABBNY (OTC), UEC, LEU, AMKR, BWXT, ENB,
  HUBB, ONTO, MOD, SMR, CCJ, NVT, ASX, DLR, GNRC, NRG, CARR, OKLO, JCI, EQIX, DUK, SO, TT, NTAP, CMI,
  PWR, ETN, TER, NEE, and n/a Samsung, Kioxia, PSTG, SGRE. Layers left empty (AI Power L2 Nuclear,
  Data Center L1 Power / L4 Cooling / L5 Operators) are no longer shown; layer numbers are kept.

  Benchmarks: SPY, QQQ, SMH (semis), XLU (utilities).

- **Each run computes (in Python, from Robinhood data):** price and day %, strength vs QQQ,
  price vs VWAP, relative volume vs the same time of day over 10 sessions, RSI14, 20/50/200-day
  SMAs, distance from the 52-week high, 20-day realized volatility, analyst targets, P/E, and
  earnings in the next 14 days.
- **Email (same look as MAG 7: bordered tables, green/red numbers, cards):** per ecosystem — layer scoreboard L1→L5 (equal-weight avg day %, vs QQQ, best/worst),
  ticker table, and a one-line read of where money is flowing along the chain. Then the top 5
  movers overall and risks/catalysts (earnings, RVOL > 2, gaps > 3%, RSI extremes). Narrative under ~400 words.

## Technical analysis (every run)
Volume (time-of-day RVOL, up/down volume, spikes) · VWAP (±1/2σ bands, slope, reclaim/loss) · Support/resistance & price action (PDH/PDL/PDC, pre-market H/L, opening range, floor pivots, prior-week H/L, prior-day volume profile POC/VAH/VAL, swing & 52-wk levels, gap, structure, breakouts) · Moving averages (5-min EMA 9/21; daily EMA 9/21, SMA 20/50/200, stack, crosses) · RSI 14 (5-min & daily, zones, divergence) · ATR 14 (daily & 5-min, range used, expected range left) · Momentum & trend strength (5-min MACD 12/26/9, ADX 14 with +DI/−DI, TTM squeeze) · Daily compression (inside day, NR7). A deterministic **bias score (−6…+6)** labels each stock BULLISH / NEUTRAL / BEARISH (plus 0–2 MACD/ADX confirmations used to rank top setups), with watch levels (bullish-above / bearish-below, target, invalidation, reward/risk in ATR). Full definitions: `technical_analysis.md`.

## How it runs
| Setting | Value |
|---|---|
| Routine | **AI Sectors Research Agent** at 7:59 and 8:59 CT. The **(9:30)** routine is **disabled** (9:30 run dropped 2026-10-13); re-enable it in claude.ai if wanted |
| Schedule | Mon–Fri at ~8:00am (pre-market) and ~9:00am US Central (runs 7:59, 8:59 — exact `:00` schedules get shifted by the server). 2 emails/day |
| Connectors | Robinhood_Agentic (read-only use) + Gmail (send only to mail11dira@gmail.com) — **must be attached to both routines** in claude.ai |
| Delivery | Gmail `send_message`, HTML tables; sender is your own address (lands in Sent + Inbox) |
| Built-in notification | Off on all routines (one email per run) |

Each firing starts a fresh cloud session with the prompt in `routine_prompt.txt`.

## How a run works (script-based, since 2026-10-13)
The routine has the DayTrading repo attached. Each run:
1. checks out branch `claude/upbeat-knuth-878qp7` and runs `python3 -m research.plan --agent <agent>` — prints the exact read-only Robinhood calls;
2. makes those calls in parallel (big results are saved to files by the harness, so the AI never re-types data);
3. runs `python3 -m research.report --agent <agent>` — reads the results from the session transcript, computes every indicator / bias score / watch level in code (`research/ta.py`, `research/analyze.py`) and renders the HTML email;
4. sends the HTML with Gmail.

If the repo or script is unavailable, the prompt falls back to the previous AI-only method (`routine_prompt_legacy.txt`).
Tests: `python -m pytest tests/test_research.py`. Re-render from saved data: `python3 -m research.report --agent <agent> --data DIR --now 2026-10-12T09:00`.

## Files
- `routine_prompt.txt` — the exact prompt the routine runs (script first, legacy fallback).
- `routine_prompt_legacy.txt` — the previous AI-only instructions (used as fallback).
- `sample_reports/` — test-run emails.

## Changing it
- **Tickers / sectors:** edit the Universe block in the routine prompt, then update `routine_prompt.txt`.
- **Pause:** disable the routine in claude.ai routines.

## Safety
- Order, cancel and exercise tools are denied in the repo's `.claude/settings.json`, and the
  prompt forbids any order, alert, scan or watchlist changes.
- Research only, not financial advice.
