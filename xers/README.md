# Xers Stocks Analysis

Reads overnight posts (previous close 16:00 ET → 09:15 ET) from the followed X accounts, ranks
the top 5 bullish and bearish tickers, and writes a mechanical day-trading plan per ticker.

Followed: @wallstengine @insiderhawk @stocksavvyshay @stockmktnewz @AIStockSavvy @bullflowIO
@quantdata @unusual_whales (edit `xers/config.py`).

Run it: ask Claude for "the Xers report" (skill: `.claude/skills/xers-premarket/SKILL.md`).

## Graph

| node | type | output | check |
|---|---|---|---|
| X1 fetch | code | `data/xers/D/tweets.json` | posts inside window; per-handle errors recorded, never fatal for others |
| X2 label | **judgment** (model) | `labels.json` | `sentiment.validate`: known post, ticker is a cashtag in it, stance/confidence valid; lexicon fallback |
| X3 rank | code | `ranking.json` | per-handle cap 1.0 per ticker; indexes/crypto excluded; ties by consensus |
| X4 levels | code | in report | prior H/L/C, pivots, PMH/PML, ATR(10), gap, pre-market RVOL from Robinhood bars |
| X5 report | code | `reports/xers/D.md` | disclaimer, silent accounts and fetch errors shown, sources linked |

Tests: `tests/test_xers.py` (part of `python -m pytest -q`).

## Trade-plan rules (mechanical, untested)
- **Long (bullish):** enter on a 5-min close above the pre-market high (prior high if no pre-market)
  after 09:35 ET. Stop = highest level at least 0.15×ATR below entry (capped at 1 ATR).
  T1/T2 = next levels at least 0.25×ATR above (ATR multiples if none). **Short** mirrors this.
- Size: 1% of $25k risk via `src/risk.py`. Half off at T1, stop to entry, flat by 15:55 ET.
- Skip if not triggered by 11:00 ET, if relative volume < 1.0× at entry, or if R:R to T1 < 1.0.

These rules are **not backtested**. Run 1 (`backtests/report.md`) found no out-of-sample edge for
opening-range breakouts; the relative-volume filter helped but did not beat SPY.

## Data access
- **X API v2** (`api.x.com`) needs a paid developer bearer token. This environment currently
  blocks the host. To enable it, allow `api.x.com` and save the token as a network secret for that
  host in the environment settings (or set `X_BEARER_TOKEN`).
- **Fallback:** paste posts into `data/xers/D/paste.txt`:
  ```
  @unusual_whales
  time: 2026-11-24 07:42
  post text with $TICKER
  ```
  (blank line between posts; `time:` is optional, ET).
- Exchange holidays are not modelled; weekends are.
