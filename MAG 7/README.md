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

## Technical analysis (every run)
Volume (time-of-day RVOL, up/down volume, spikes) · VWAP (±1/2σ bands, slope, reclaim/loss) · Support/resistance & price action (PDH/PDL/PDC, pre-market H/L, opening range, floor pivots, swing & 52-wk levels, gap, structure, breakouts) · Moving averages (5-min EMA 9/21; daily EMA 9/21, SMA 20/50/200, stack, crosses) · RSI 14 (5-min & daily, zones, divergence) · ATR 14 (daily & 5-min, range used, expected range left). A deterministic **bias score (−6…+6)** labels each stock BULLISH / NEUTRAL / BEARISH, with watch levels (bullish-above / bearish-below, target, invalidation, reward/risk in ATR). Full definitions: `technical_analysis.md`.

## How it runs
| Setting | Value |
|---|---|
| Routines | **MAG 7 Research Agent** (`trig_012DY3peEQUikJ9MBxYuLXpG`) at 7:59 and 8:59, and **MAG 7 Research Agent (9:30)** (`trig_01TZoDuVzveBgkv4RqgL2pSs`) at 9:29 — same prompt; routines can't fire < 1 hour apart, so 9:30 needs its own |
| Schedule | Mon–Fri at ~8:00am, 9:00am, 9:30am US Central (runs 1 minute early: 7:59, 8:59, 9:29 — exact `:00` schedules get shifted by the server). 3 emails/day. The 8:00 run is pre-market |
| Connectors | Robinhood_Agentic (read-only use) + Gmail (send only to mail11dira@gmail.com) — **must be attached to both routines** in claude.ai |
| Delivery | Gmail `send_message`, HTML table; sender is your own address (lands in Sent + Inbox) |
| Built-in notification | Off on the 9:30 routine. **Still ON for the main MAG 7 routine** — turn Email off in its claude.ai settings for one email per run |
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
