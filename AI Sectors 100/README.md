# AI Sectors 100 — Stock Research Agent

**One agent that replaces AI Sectors + Modern AI Sectors** (merged 2026-10-20). Research-only day-trading report on
the **best 100 unique stocks** for day trading, in the Modern AI Sectors email format (sector scoreboard, weekend
checklist, per-sector tables, top setups), built from Robinhood data and emailed to mail11dira@gmail.com.
**No orders are ever placed.** MAG 7 stays in its own agent (`../MAG 7`) and is excluded here; no ETFs.

## How the 100 were picked (20-day Robinhood data, 2026-09-18 → 2026-10-16)
1. Candidates (120): every stock from AI Sectors (32) and Modern AI Sectors (60), the 5 extra names that passed the
   last screen (ABNB, DKNG, RIVN, F, GM) and 36 more high-volume names (APP, CRM, NOW, SNOW, DDOG, ADBE, MDB, ZS, MARA,
   RIOT, CLSK, HIMS, SOUN, ROKU, TTD, QCOM, ON, MCHP, TXN, NKE, LULU, UNH, CVX, XOM, OXY, SLB, ENPH, FSLR, BE, WULF,
   PYPL, INTU, MSCI, COHR, ALAB, NVTS).
2. Hard screen: average dollar volume ≥ $200M/day, price ≥ $5, daily ATR ≥ 2.5% → 111 passed.
   Failed: CVX, MSCI, OXY, PYPL, ROKU, XOM (ATR too low); ENPH, NVTS, SOUN (volume).
3. Score = average of the percentile ranks of dollar volume (liquidity) and ATR % (range). Top 100 kept.
   Cut at 101-111: ABNB, LULU, SLB, ALB, AEM, VRTX, DHI, GM, F, BIDU, PHM.
4. Mix: 13 were in both old agents, 19 only in AI Sectors, 41 only in Modern AI Sectors, 27 new.
   Dropped from the old agents: AEM, ALB, BIDU, DHI, PHM, VRTX (ranked below 100), plus every ETF.

Rank 1 = best day-trading score. Re-run the ranking every few months: the list is in `research/universe.py` (`AI100`).

## Universe — 15 sectors, 100 stocks (benchmarks SPY, QQQ)

**01 Semiconductors / Memory** (15)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 5 | SNDK | $13.74B | 7.5% | AI Sectors + Modern |
| 13 | MU | $27.79B | 5.6% | AI Sectors + Modern |
| 9 | INTC | $11.80B | 6.5% | AI Sectors + Modern |
| 21 | AMD | $12.96B | 5.2% | AI Sectors + Modern |
| 37 | AVGO | $7.93B | 3.5% | AI Sectors + Modern |
| 8 | MRVL | $5.33B | 7.0% | AI Sectors |
| 7 | WDC | $3.73B | 7.7% | AI Sectors |
| 16 | SKHY | $3.14B | 6.5% | AI Sectors |
| 18 | ARM | $1.76B | 7.7% | AI Sectors |
| 22 | ALAB | $1.48B | 8.4% | new |
| 46 | QCOM | $2.05B | 4.2% | new |
| 49 | TSM | $4.77B | 3.0% | AI Sectors |
| 67 | ON | $0.85B | 4.9% | new |
| 79 | TXN | $1.47B | 3.1% | new |
| 86 | MCHP | $0.69B | 4.2% | new |

**02 Semiconductor Equipment** (5)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 27 | LRCX | $2.65B | 5.5% | AI Sectors |
| 28 | AMAT | $3.10B | 5.1% | AI Sectors |
| 42 | KLAC | $1.72B | 4.9% | AI Sectors |
| 54 | ASML | $2.60B | 3.3% | AI Sectors |
| 41 | TER | $0.98B | 6.5% | Modern |

**03 AI Infrastructure / Networking / Optical** (10)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 12 | DELL | $3.87B | 7.0% | AI Sectors + Modern |
| 26 | SMCI | $1.39B | 8.1% | Modern |
| 32 | HPE | $1.35B | 7.2% | AI Sectors |
| 39 | VRT | $1.16B | 5.6% | AI Sectors + Modern |
| 63 | ANET | $1.03B | 4.7% | AI Sectors + Modern |
| 78 | CSCO | $2.02B | 2.8% | AI Sectors |
| 2 | LITE | $4.70B | 8.6% | AI Sectors |
| 10 | COHR | $2.11B | 9.7% | new |
| 15 | CRDO | $1.73B | 8.7% | AI Sectors |
| 19 | AAOI | $1.09B | 12.5% | AI Sectors |

**04 Neo-Cloud / AI Hosting** (6)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 1 | NBIS | $4.10B | 10.5% | AI Sectors + Modern |
| 4 | CRWV | $3.06B | 9.9% | AI Sectors + Modern |
| 11 | IREN | $1.72B | 10.6% | AI Sectors + Modern |
| 36 | CIFR | $0.58B | 14.7% | AI Sectors |
| 40 | APLD | $0.57B | 9.8% | AI Sectors |
| 47 | WULF | $0.48B | 9.7% | new |

**05 Software / AI Apps** (10)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 17 | ORCL | $4.23B | 5.6% | AI Sectors |
| 34 | PLTR | $4.50B | 4.2% | Modern |
| 45 | APP | $1.43B | 5.4% | new |
| 52 | CRM | $2.10B | 3.8% | new |
| 55 | NOW | $1.49B | 4.6% | new |
| 35 | SNOW | $1.52B | 5.6% | new |
| 31 | MDB | $1.16B | 7.5% | new |
| 64 | DDOG | $0.78B | 5.4% | new |
| 76 | INTU | $1.09B | 3.9% | new |
| 81 | ADBE | $1.07B | 3.6% | new |

**06 Cybersecurity** (5)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 29 | PANW | $2.09B | 5.6% | Modern |
| 30 | CRWD | $2.25B | 5.4% | Modern |
| 44 | NET | $1.01B | 5.9% | Modern |
| 69 | ZS | $0.62B | 5.3% | new |
| 89 | FTNT | $0.62B | 4.0% | Modern |

**07 Power / Energy / Nuclear** (7)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 3 | BE | $3.77B | 9.0% | new |
| 43 | GEV | $2.03B | 4.6% | AI Sectors + Modern |
| 53 | CEG | $1.13B | 5.0% | AI Sectors + Modern |
| 56 | VST | $1.11B | 4.9% | AI Sectors |
| 58 | OKLO | $0.34B | 8.2% | Modern |
| 83 | ETN | $0.88B | 3.8% | Modern |
| 95 | FSLR | $0.42B | 4.6% | new |

**08 Crypto / Fintech / Banks** (10)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 14 | MSTR | $3.27B | 7.1% | Modern |
| 23 | HOOD | $2.18B | 6.0% | Modern |
| 33 | COIN | $1.54B | 6.4% | Modern |
| 38 | CRCL | $0.93B | 7.2% | Modern |
| 50 | MARA | $0.40B | 10.1% | new |
| 48 | RIOT | $0.34B | 10.6% | new |
| 57 | CLSK | $0.20B | 10.4% | new |
| 77 | SOFI | $0.80B | 4.7% | Modern |
| 88 | AFRM | $0.31B | 5.5% | Modern |
| 75 | GS | $2.05B | 2.8% | Modern |

**09 Space / Aerospace** (3)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 20 | RKLB | $1.53B | 8.6% | Modern |
| 24 | ASTS | $0.89B | 11.3% | Modern |
| 84 | BA | $1.62B | 2.7% | Modern |

**10 Quantum** (3)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 25 | IONQ | $1.11B | 9.0% | Modern |
| 65 | QBTS | $0.25B | 8.3% | Modern |
| 71 | RGTI | $0.24B | 7.6% | Modern |

**11 Consumer / Internet** (10)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 51 | SHOP | $1.61B | 4.6% | Modern |
| 66 | NFLX | $2.47B | 2.7% | Modern |
| 68 | RDDT | $0.65B | 5.3% | Modern |
| 73 | CVNA | $0.53B | 5.6% | Modern |
| 70 | NKE | $1.63B | 3.1% | new |
| 85 | DKNG | $0.32B | 5.5% | new |
| 94 | UBER | $1.09B | 2.7% | Modern |
| 100 | TTD | $0.24B | 4.8% | new |
| 91 | RIVN | $0.36B | 4.8% | new |
| 93 | BABA | $0.94B | 2.9% | Modern |

**12 Health / Biotech** (4)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 6 | MRNA | $3.69B | 7.7% | Modern |
| 61 | LLY | $2.72B | 2.8% | Modern |
| 60 | UNH | $2.26B | 3.0% | new |
| 74 | HIMS | $0.32B | 6.9% | new |

**13 Travel / Airlines / Cruise** (5)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 82 | AAL | $0.83B | 3.9% | Modern |
| 92 | UAL | $0.49B | 4.3% | Modern |
| 97 | DAL | $0.61B | 3.4% | Modern |
| 90 | RCL | $0.82B | 3.4% | Modern |
| 96 | CCL | $0.64B | 3.3% | Modern |

**14 Metals / Miners** (5)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 62 | CDE | $0.60B | 5.7% | Modern |
| 72 | HL | $0.60B | 5.5% | Modern |
| 80 | MP | $0.26B | 6.1% | Modern |
| 87 | FCX | $0.77B | 3.9% | Modern |
| 99 | NEM | $0.62B | 3.2% | Modern |

**15 Industrials / Housing** (2)

| Rank | Stock | $ volume/day | ATR % | From |
|---|---|---|---|---|
| 59 | CAT | $2.01B | 3.8% | AI Sectors |
| 98 | LEN | $0.46B | 4.0% | Modern |

## Email (same as Modern AI Sectors)
1. Market snapshot (SPY, QQQ) + tape (leading / lagging sector)
2. Sector scoreboard — avg day %, vs QQQ, 20-day RS vs SPY, avg bias, # holding 8/21, best / worst
3. Weekend checklist — new highs · holding the 8/21 EMA trend · outperforming SPY/QQQ (20d) · relative strength by
   sector · breaking out of a base · volume expanding
4. One table per sector: Ticker | Price | Day % | vs QQQ | 20d RS | Bias | vs VWAP | RVOL | RSI 5m/D | 8/21 | Nearest S/R | ADX
5. Top 5 setups (full technical cards) and risks / catalysts. Bullish = green, bearish = red everywhere.

## Technical analysis (every run)
Same engine as the other agents: Volume (RVOL, up/down volume, spikes) · VWAP (±1/2σ, slope, reclaim/loss) ·
Levels (PDH/PDL/PDC, pre-market H/L, opening range, pivots, prior-week H/L, prior-day volume profile POC/VAH/VAL,
20d & 52w, round numbers) · MAs (5-min EMA 9/21; daily EMA 8/9/21, SMA 20/50/200) · RSI 14 · ATR 14 · MACD · ADX/DMI ·
TTM squeeze · inside day / NR7 · bias score −6…+6 with MACD/ADX confirmations · watch levels (targets 0.5–2 ATR).
Full definitions: `technical_analysis.md`.

## How it runs
| Setting | Value |
|---|---|
| Routine | **AI Sectors 100 Research Agent** (`trig_01D3Gr9p5a4cJvwRkuHVThUg`, the former Modern AI Sectors routine) — Mon–Fri 7:59 and 8:59 CT |
| Replaces | AI Sectors routine (`trig_01BSEzw8DL1JRFyRSmVnQK6B`) — **disabled** 2026-10-20, not deleted |
| Connectors | Robinhood_Agentic (read-only use) + Gmail (send only to mail11dira@gmail.com) |
| Prompt | `routine_prompt.txt` (`research.plan --agent ai100` → calls → `research.report --agent ai100` → Gmail) |
| Data per run | 52 read-only Robinhood calls (6 quotes, 21 + 11 five-minute, 11 daily, earnings, 2 ratings) |
| Test | `python -m pytest -q`; real-data sample: `sample_reports/2026-10-19_close_test.html` |
