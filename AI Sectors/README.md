# AI Sectors — Stock Research Agent

An hourly, research-only report on AI-sector stocks, built from Robinhood data and emailed to
mail11dira@gmail.com. Same setup as `../MAG 7`. **No orders are ever placed.**

## What it does
- **Universe: 3 ecosystems × 5 layers × 6 tickers** (about 75 unique symbols; repeats are fetched once):

  **1. Memory Ecosystem**
  | Layer | Sector | Tickers |
  |---|---|---|
  | 1 | Equipment | ASML, AMAT, LRCX, KLAC, TER, ONTO |
  | 2 | Memory Makers | MU, SK Hynix*, Samsung*, WDC, SNDK, Kioxia* |
  | 3 | Packaging & Test | TSM, AMKR, ASE (ASX), BESI*, DISCO*, ASMPT* |
  | 4 | Storage Platforms | PSTG, NTAP, DELL, HPE, WDC, SNDK |
  | 5 | AI Demand | NVDA, AVGO, AMD, META, AMZN, GOOGL |

  **2. AI Power Stack**
  | Layer | Sector | Tickers |
  |---|---|---|
  | 1 | Generation | VST, CEG, NRG, NEE, DUK, SO |
  | 2 | Nuclear | CCJ, UEC, BWXT, LEU, SMR, OKLO |
  | 3 | Grid | ETN, PWR, HUBB, GEV, ABB*, SGRE* |
  | 4 | Power Management | ENB†, GNRC, CAT, CMI, NVT, VRT |
  | 5 | Demand Centers | AMZN, MSFT, GOOGL, META, ORCL, DLR |

  **3. Data Center Ecosystem**
  | Layer | Sector | Tickers |
  |---|---|---|
  | 1 | Power | VST, CEG, ETN, PWR, GEV, ENB† |
  | 2 | Compute | NVDA, AMD, AVGO, INTC, ARM, MU |
  | 3 | Networking | ANET, MRVL, CRDO, CSCO, LITE, AAOI |
  | 4 | Cooling | VRT, TT, MOD, CARR, JCI, NVT |
  | 5 | Operators | DLR, EQIX, AMZN, MSFT, GOOGL, ORCL |

  Benchmarks: SPY, QQQ, SMH (semis), XLU (utilities).

  **\* Foreign listings — Robinhood mapping (checked 2026-10-13):**
  | Name | Robinhood symbol |
  |---|---|
  | SK Hynix | SKHY (ADR) |
  | BESI | BESIY (OTC) |
  | DISCO | DSCSY (OTC) |
  | ASMPT | ASMVY (OTC, thin) |
  | ABB | ABBNY (OTC) |
  | Samsung, Kioxia, Siemens Gamesa (SGRE, delisted) | not on Robinhood — shown as n/a, excluded from averages |

  † ENB trades on the NYSE and is tracked normally; the † is kept as you listed it.
- **Each run computes (in Python, from Robinhood data):** price and day %, strength vs QQQ,
  price vs VWAP, relative volume vs the same time of day over 10 sessions, RSI14, 20/50/200-day
  SMAs, distance from the 52-week high, 20-day realized volatility, analyst targets, P/E, and
  earnings in the next 14 days.
- **Email (per ecosystem):** layer scoreboard L1→L5 (equal-weight avg day %, vs QQQ, best/worst),
  ticker table, and a one-line read of where money is flowing along the chain. Then the top 5
  movers overall and risks/catalysts (earnings, RVOL > 2, gaps > 3%, RSI extremes). Narrative under ~400 words.

## Technical analysis (every run)
Volume (time-of-day RVOL, up/down volume, spikes) · VWAP (±1/2σ bands, slope, reclaim/loss) · Support/resistance & price action (PDH/PDL/PDC, pre-market H/L, opening range, floor pivots, swing & 52-wk levels, gap, structure, breakouts) · Moving averages (5-min EMA 9/21; daily EMA 9/21, SMA 20/50/200, stack, crosses) · RSI 14 (5-min & daily, zones, divergence) · ATR 14 (daily & 5-min, range used, expected range left). A deterministic **bias score (−6…+6)** labels each stock BULLISH / NEUTRAL / BEARISH, with watch levels (bullish-above / bearish-below, target, invalidation, reward/risk in ATR). Full definitions: `technical_analysis.md`.

## How it runs
| Setting | Value |
|---|---|
| Routines | **AI Sectors Research Agent** (`trig_01BSEzw8DL1JRFyRSmVnQK6B`) at 7:59 and 8:59, and **AI Sectors Research Agent (9:30)** (`trig_01BRGe391GXt4kzok9eotfwp`) at 9:29 — same prompt; routines can't fire < 1 hour apart, so 9:30 needs its own |
| Schedule | Mon–Fri at ~8:00am, 9:00am, 9:30am US Central (runs 1 minute early: 7:59, 8:59, 9:29 — exact `:00` schedules get shifted by the server). 3 emails/day. The 8:00 run is pre-market |
| Connectors | Robinhood_Agentic (read-only use) + Gmail (send only to mail11dira@gmail.com) — **must be attached to both routines** in claude.ai |
| Delivery | Gmail `send_message`, HTML tables; sender is your own address (lands in Sent + Inbox) |
| Built-in notification | Off on all routines (one email per run) |

Each firing starts a fresh cloud session with the prompt in `routine_prompt.txt`.

## Files
- `routine_prompt.txt` — the exact prompt the routine runs (keep in sync if you edit the routine).
- `sample_reports/` — test-run emails.

## Changing it
- **Tickers / sectors:** edit the Universe block in the routine prompt, then update `routine_prompt.txt`.
- **Pause:** disable the routine in claude.ai routines.

## Safety
- Order, cancel and exercise tools are denied in the repo's `.claude/settings.json`, and the
  prompt forbids any order, alert, scan or watchlist changes.
- Research only, not financial advice.
