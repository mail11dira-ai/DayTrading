# AI Sectors 100 — Stock Research Agent

Research-only day-trading report on a fixed list of **101 unique stocks** in **16 sectors** (benchmarks SPY, QQQ),
built from Robinhood data and emailed to mail11dira@gmail.com Mon-Fri. **No orders are ever placed.**
MAG 7 stays in its own agent (`../MAG 7`) and is excluded here; no ETFs.

## Universe (updated 2026-10-28)
The list is the top 100 from the 2026-10-27 close ranking of the AI Sectors 100 and Super 100 universes (MAG 7
excluded): stocks ranked by bullish bias, then in-play score, then confirmations. Only 82 of the 100 have a bullish
bias; the last 18 are neutral (bias 0) or slightly bearish. The list is kept as given: no day-trading dollar-volume
screen, and no Modern AI Sectors notes. The list is in `research/universe.py` (`AI100`). Re-rank every few months.

**+1 (2026-10-28): CRWV** added as the best stock not already listed: #2 of 249 on a day-trading screen (ATR % x trend-day ratio, $ volume >= $2B/day), behind only SOXL (a leveraged ETF; no ETFs here). 11.8% ATR, $3.7B/day, trend-day ratio 0.59.

The previous list (120 candidates, screened on dollar volume and ATR) is in the git history before 2026-10-28.

| # | Sector | Stocks |
|---|---|---|
| 01 | Semiconductors & Memory (17) | TXN, ALAB, MCHP, MRVL, AVGO, AMD, INTC, QCOM, ON, SNDK, TSM, MU, KLAC, LRCX, AMAT, ASML, TER |
| 02 | AI Infrastructure / Networking / Optical (8) | SMCI, HPE, DELL, ANET, LITE, COHR, CRDO, AAOI |
| 03 | Neo-Cloud / AI Hosting (5) | NBIS, IREN, CIFR, WULF, CRWV |
| 04 | Software & AI Apps (5) | DDOG, INTU, APP, IBM, SNPS |
| 05 | Cybersecurity (3) | PANW, CRWD, FTNT |
| 06 | Power / Energy / Nuclear (7) | GEV, VST, OKLO, ETN, FSLR, SO, NEE |
| 07 | Metals & Miners (4) | MP, CDE, HL, NEM |
| 08 | Materials & Real Estate (2) | LIN, AMT |
| 09 | Quantum (3) | IONQ, RGTI, QBTS |
| 10 | Industrials & Defense (6) | UNP, GE, HON, CAT, DE, RKLB |
| 11 | Airlines, Travel & Cruise (6) | DAL, UAL, AAL, RCL, CCL, ABNB |
| 12 | Consumer & Internet (11) | SBUX, NKE, LOW, HD, ORLY, RIVN, CVNA, DIS, BABA, DKNG, LEN |
| 13 | Consumer Staples (2) | WMT, PG |
| 14 | Healthcare (8) | MRNA, VRTX, JNJ, ABBV, LLY, UNH, TMO, ISRG |
| 15 | Banks, Payments & Insurance (8) | GS, WFC, BLK, V, MA, AFRM, SOFI, PGR |
| 16 | Crypto & Bitcoin Miners (6) | MSTR, COIN, CRCL, RIOT, CLSK, MARA |

Benchmarks: SPY, QQQ. Sector grouping is by business line.

## Email (short since 2026-10-28, one part)
1. Market snapshot (SPY, QQQ) + tape (leading / lagging sector)
2. Sector scoreboard (day-trading only): avg day %, vs QQQ, 30-min RS vs QQQ, avg bias, best / worst stock per sector
3. Top 3 setups (ranked by in-play score, then bias), with short cards
4. Risks / catalysts

No weekend checklist, no per-sector tables, and no daily-timeframe items (20-day RS, 8/21 holding, daily RSI), since 2026-10-28; the daily ATR is kept as the range unit for the in-play score. The bias score still uses the daily MA stack as an input, so its formula is unchanged.

## Technical analysis (every run)
Same engine as the other agents: Volume (RVOL, up/down volume, spikes) · VWAP (±1/2σ, slope, reclaim/loss) ·
Levels (PDH/PDL/PDC, pre-market H/L, opening range, pivots, prior-week H/L, prior-day volume profile POC/VAH/VAL,
20d & 52w, round numbers) · MAs (5-min EMA 9/21; daily EMA 8/9/21, SMA 20/50/200) · RSI 14 · ATR 14 · MACD · ADX/DMI ·
TTM squeeze · inside day / NR7 · bias score −6…+6 with MACD/ADX confirmations · watch levels (targets 0.5–2 ATR).
Added 2026-10-20: **volume-confirmed opening-range breakout (ORB)**, **pre-market volume + gap quality** (gap-and-go / fade risk), **intraday relative strength vs QQQ** (15/30 min) and **market breadth / regime + VIX** in the snapshot. Full definitions: `technical_analysis.md`. The bias score is checked against what happened next in `../backtests/bias_validation.md`.

## How it runs
| Setting | Value |
|---|---|
| Routines | **AI Sectors 100 Research Agent (8:45)** (`trig_01D3Gr9p5a4cJvwRkuHVThUg`, repo attached) and **(1:30)** (`trig_01BRGe391GXt4kzok9eotfwp`, no repo attached) — Mon–Fri 8:45 and 1:30 pm CT, on claude-haiku-5-5 |
| Replaces | Earlier Modern AI Sectors and AI Sectors routines; the Super 100 agent is separate (`../Super 100`) |
| Connectors | Robinhood_Agentic (read-only use) + Gmail (send only to mail11dira@gmail.com) |
| Prompt | `routine_prompt.txt` (`research.plan --agent ai100` → calls → `research.report --agent ai100` → Gmail) |
| Data per run | 30 read-only Robinhood calls (quotes, extended-hours 5-min, daily; no analyst ratings) |
| Test | `python -m pytest -q`; real-data sample: `sample_reports/2026-10-19_close_test.html` |
