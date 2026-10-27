# Super 100 Research Agent

Replaces the MAG 7 agent (2026-10-27). Research only - no orders. Emails mail11dira@gmail.com
Mon-Fri at 8:30 and 8:59 CT. Code: `python3 -m research.plan --agent super100`, then
`python3 -m research.report --agent super100`.

**Universe: 100 stocks** from the user's list (MSFT appeared twice, so SPCX was added as #100), grouped in 13 sectors. Kept exactly as given:
no day-trading screen. Berkshire is `BRK.B` on Robinhood. Benchmarks SPY, QQQ, plus the VIX.

| # | Sector | Stocks | Tickers |
|---|---|---|---|
| 01 | Mega-cap Tech | 6 | MSFT, NVDA, AAPL, GOOGL, AMZN, META |
| 02 | Semiconductors & Equipment | 12 | AVGO, TSM, AMD, MU, QCOM, INTC, MRVL, ASML, AMAT, LRCX, KLAC, SNPS |
| 03 | Software & Cloud | 11 | ORCL, NOW, CRM, ADBE, IBM, ACN, PLTR, APP, DDOG, SNOW, NBIS |
| 04 | Cybersecurity & Networking | 5 | PANW, CRWD, NET, ANET, CSCO |
| 05 | Internet & Platforms | 8 | NFLX, BKNG, UBER, ABNB, MELI, SHOP, BABA, DIS |
| 06 | Consumer Discretionary | 9 | TSLA, HD, LOW, TJX, MCD, SBUX, CMG, NKE, ORLY |
| 07 | Consumer Staples | 5 | WMT, COST, PG, KO, PEP |
| 08 | Healthcare | 9 | LLY, UNH, JNJ, ABBV, MRK, ABT, TMO, ISRG, VRTX |
| 09 | Banks & Brokers | 7 | JPM, BAC, WFC, GS, MS, SCHW, BLK |
| 10 | Payments, Insurance & Data | 7 | V, MA, AXP, BRK.B, PGR, SPGI, COIN |
| 11 | Industrials & Defense | 10 | GE, HON, RTX, LMT, CAT, DE, UNP, BA, ETN, SPCX |
| 12 | Energy & Utilities | 6 | XOM, CVX, NEE, CEG, VST, SO |
| 13 | Materials & Real Estate | 5 | LIN, FCX, NEM, PLD, AMT |

**Email:** 1. market deep dive (SPY / QQQ / VIX, implied move band, SPY and QQQ cards) - 2. sector scoreboard -
3. weekend checklist - 4. top 5 setups (ranked by in-play score, then bias) with cards - 5. risks / catalysts
(MAG 7 thresholds: gaps > 2%, RSI 70/30). Indicator rules: `../MAG 7/technical_analysis.md` (same engine).
