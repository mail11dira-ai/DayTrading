# AI Sectors — Stock Research Agent

An hourly, research-only report on AI-sector stocks, built from Robinhood data and emailed to
mail11dira@gmail.com. Same setup as `../MAG 7`. **No orders are ever placed.**

## What it does
- **Universe (15 stocks, 4 sectors):**
  | Sector | Tickers |
  |---|---|
  | AI Chips | NVDA, AMD, AVGO, TSM, MU |
  | AI Infrastructure (networking, servers, power) | ANET, VRT, SMCI, CEG |
  | AI Cloud | ORCL, CRWV |
  | AI Software | PLTR, NOW, CRM, SNOW |
  Benchmarks: SPY, QQQ, SMH (semiconductor ETF). MSFT/GOOGL/AMZN/META are left out because the MAG 7 agent already covers them.
- **Each run computes (in Python, from Robinhood data):** price and day %, strength vs QQQ,
  price vs VWAP, relative volume vs the same time of day over 10 sessions, RSI14, 20/50/200-day
  SMAs, distance from the 52-week high, 20-day realized volatility, analyst targets, P/E, and
  earnings in the next 14 days.
- **Email:** sector scoreboard (equal-weight avg day % per sector, vs QQQ, best/worst) + results
  table grouped by sector + top 3 moves of the hour + risks/catalysts, under ~500 words.

## How it runs
| Setting | Value |
|---|---|
| Routine | **AI Sectors Research Agent** (`trig_01BSEzw8DL1JRFyRSmVnQK6B`) in claude.ai routines |
| Schedule | Mon–Fri, hourly 7:58am–1:58pm US Central — `CRON_TZ=America/Chicago 58 7-13 * * 1-5` (7 runs/day) |
| Connectors | Robinhood_Agentic (read-only use), Gmail (send only to mail11dira@gmail.com) — **add both in the routine settings** |
| Delivery | Gmail `send_message`, HTML tables; sender is your own address (lands in Sent + Inbox) |
| Built-in notification | Off (one email per run) |

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
