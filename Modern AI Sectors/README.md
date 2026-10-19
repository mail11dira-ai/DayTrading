# Modern AI Sectors — Stock Research Agent

A research-only day-trading report on 11 modern market sectors plus Neo-Cloud — sector ETFs and their
leader stocks — built from Robinhood data and emailed to mail11dira@gmail.com. Same setup and technicals as
`../MAG 7` and `../AI Sectors`. **No orders are ever placed.**

## Universe — 12 sectors, 84 symbols (39 ETFs + 45 stocks), benchmarks SPY & QQQ
Source: the user's sector map (2026-10-19) + Neo-Cloud. Each ticker is shown once (first listing);
NVDA and TSLA are excluded because the MAG 7 agent covers them.

| # | Sector | Sector ETFs | Leader stocks |
|---|---|---|---|
| 01 | Semiconductors / Memory | SMH, DRAM, SOXX, XSD | AMD, AVGO, MU, SNDK, INTC (NVDA → MAG 7) |
| 02 | AI Infrastructure / Data Centers | DTCR, PSI, PSTG (n/a — not on Robinhood) | DELL, SMCI, VRT, ANET |
| 03 | Software / Cybersecurity | IGV, CIBR, HACK, SKYY | PLTR, CRWD, PANW, FTNT, NET |
| 04 | Power / Grid / Nuclear | GRID, XLI, NLR, PAVE, URA | GEV, CEG, ETN, OKLO (VRT → 02) |
| 05 | Crypto / Fintech | ARKF, WGMI, BLOK, BITO, IBIT | HOOD, COIN, CRCL, MSTR |
| 06 | Space / Defense | ARKX, ITA, UFO, XAR | ASTS, RKLB, LMT, RTX, BA |
| 07 | Quantum | QTUM | IONQ, RGTI, QBTS, QUBT |
| 08 | Robotics / Automation | BOTZ, ARKQ | ACHR, TER (TSLA → MAG 7, PLTR → 03) |
| 09 | Real Assets / Resources | GLD, SLV, COPX, REMX | FCX, TECK, SCCO, MP, ALB |
| 10 | Economy / Risk | IWM, XLF, XLE, JETS | (same as the ETFs; SPY/QQQ are the benchmarks) |
| 11 | Health / Biotech | XBI, XLV, IBB, ARKG | VRTX, LLY, MRNA, ABBV |
| 12 | Neo-Cloud | — | NBIS, CRWV, IREN |

IGV and CIBR were also listed under 02 (AI infra / AI exposure); they are shown once, in 03.

## Email
1. Market snapshot (SPY, QQQ) + tape (leading / lagging sector)
2. **Sector scoreboard** — ETFs avg day %, leaders avg day %, vs QQQ, 20-day RS vs SPY, avg bias, # holding 8/21, best / worst
3. **Weekend checklist** (computed in code from daily bars):
   1. Making new highs — at a 52-week or 20-day high
   2. Holding the 8/21 trend — price > daily EMA8 > EMA21 (lost = below EMA21)
   3. Outperforming SPY / QQQ — 20-day return above both
   4. Relative strength by sector — average 20-day return vs SPY, strongest / weakest 3
   5. Breaking out of a base — 20-day range ≤ 5 daily ATRs and price above its high
   6. Volume expanding — 5-day avg volume ≥ 1.3× the 50-day average, or RVOL ≥ 1.5
4. One table per sector: Type (ETF/Stock) | Ticker | Price | Day % | vs QQQ | 20d RS | Bias | vs VWAP | RVOL | RSI 5m/D | 8/21 | Nearest S/R | ADX
5. Top 5 setups (full technical cards) and risks / catalysts

Bullish = green, bearish = red everywhere.

## Technical analysis (every run)
Same engine as MAG 7 / AI Sectors: Volume (time-of-day RVOL, up/down volume, spikes) · VWAP (±1/2σ bands, slope, reclaim/loss) · Support/resistance & price action (PDH/PDL/PDC, pre-market H/L, opening range, floor pivots, prior-week H/L, prior-day volume profile POC/VAH/VAL, swing & 52-wk levels, gap, structure, breakouts) · Moving averages (5-min EMA 9/21; daily EMA 8/9/21, SMA 20/50/200, stack, crosses) · RSI 14 · ATR 14 · Momentum & trend strength (5-min MACD 12/26/9, ADX 14 with +DI/−DI, TTM squeeze) · Daily compression (inside day, NR7). Deterministic **bias score (−6…+6)** with 0–2 MACD/ADX confirmations and watch levels (targets 0.5–2 ATR). Full definitions: `technical_analysis.md`.

## How it runs
| Setting | Value |
|---|---|
| Routine | **Modern AI Sectors Research Agent** — Mon–Fri 7:59 and 8:59 CT (`CRON_TZ=America/Chicago 59 7,8 * * 1-5`) |
| Connectors | Robinhood_Agentic (read-only use) + Gmail (send only to mail11dira@gmail.com) — attach both to the routine in claude.ai |
| Prompt | `routine_prompt.txt` (script-first: `research.plan --agent modern` → calls → `research.report --agent modern` → Gmail) |
| Data per run | 43 read-only Robinhood calls (5 quotes, 18 + 9 five-minute, 9 daily, earnings, ratings) |
| Test | `python -m pytest -q`; sample from real data: `sample_reports/2026-10-16_close_test.html` |
