# MAG 7 — Stock Research Agent

An hourly, research-only report on the Magnificent 7 built from Robinhood data and emailed to
mail11dira@gmail.com. **No orders are ever placed.**

## What it does
- **Universe:** AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA — benchmarked against SPY and QQQ.
- **Each run computes (in Python, from Robinhood data):** price and day %, strength vs QQQ,
  price vs VWAP, relative volume vs the same time of day over 10 sessions, RSI14, 20/50/200-day
  SMAs, distance from the 52-week high, 20-day realized volatility, analyst targets, P/E, and
  MAG 7 earnings in the next 14 days.
- **Email:** results table + top 3 moves of the hour + risks/catalysts, under ~400 words.

## How it runs
| Setting | Value |
|---|---|
| Routine | **MAG 7 Research Agent** (`trig_012DY3peEQUikJ9MBxYuLXpG`) in claude.ai routines |
| Schedule | Mon–Fri, hourly 7:58am–1:58pm US Central — `CRON_TZ=America/Chicago 58 7-13 * * 1-5` (7 runs/day) |
| Connectors | Robinhood_Agentic (read-only use), Gmail (send only to mail11dira@gmail.com) |
| Delivery | Gmail `send_message`, HTML table; sender is your own address (lands in Sent + Inbox) |
| Built-in notification | Turn **Email off** in the routine settings so you get one email per run |
| Cost | ~$0.27–0.35 per run (test runs) |

Each firing starts a fresh cloud session with the prompt in `routine_prompt.txt`.

## Files
- `routine_prompt.txt` — the exact prompt the routine runs (keep in sync if you edit the routine).
- `agent_spec.md` — original spec and design notes.
- `sample_reports/2026-10-11_test2_email.html` — the test email as delivered (open in a browser).
- `sample_reports/2026-10-11_test1.md` — first test run (before Gmail was attached).

## Changing it
- **Prompt:** edit the routine in claude.ai (or ask Claude to `update_trigger`), then update `routine_prompt.txt`.
- **Pause:** disable the routine in claude.ai routines.
- **Schedule/tickers:** change the cron or the Universe line in the prompt.

## Safety
- Order, cancel and exercise tools are denied in the repo's `.claude/settings.json`, and the
  prompt forbids any order, alert, scan or watchlist changes.
- Research only, not financial advice.
