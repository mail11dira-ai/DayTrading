# Super 10 Research Agent

Research only - no orders. Named "Super 10" (was "Super 100"; the agent key stays `super100`). Emails mail11dira@gmail.com Mon-Fri at 8:45 and 9:45 CT. Code:
`python3 -m research.plan --agent super100`, then `python3 -m research.report --agent super100`.

**Universe: 12 stocks** (updated 2026-10-28, the user's list only): GOOGL, AAPL, MSFT, META, AMZN, NVDA, AVGO, AMD,
VRT, CRWD, TSLA, SPCX. Nothing else is added and no day-trading screen is applied. Benchmarks SPY and QQQ.

| # | Sector | Tickers |
|---|---|---|
| 01 | Mega-cap Tech | GOOGL, AAPL, MSFT, META, AMZN, NVDA |
| 02 | Semiconductors | AVGO, AMD |
| 03 | AI Data Center Infrastructure | VRT |
| 04 | Cybersecurity | CRWD |
| 05 | Autos | TSLA |
| 06 | Space / Aerospace | SPCX |

**Email:** market deep dive (SPY / QQQ / VIX, implied move band, SPY and QQQ cards), sector scoreboard, top 3
setups with cards, and risks / catalysts (gaps > 2%, RSI 70/30). Indicator rules: `../MAG 7/technical_analysis.md`
(same engine).
