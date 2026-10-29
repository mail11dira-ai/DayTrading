# UNUSUAL Options Flow Agent

Research only - no orders. Emails mail11dira@gmail.com Mon-Fri at 9:35 am and 1:35 pm CT. Code:
`research/unusual.py` (tests in `tests/test_research.py`).

**What it does:** scans the whole market for unusual options activity, keeps single stocks (ETFs drop out: index-ETF
flow is mostly hedging), pulls the nearest-expiry contracts around the price for the 5 most bullish and 5 most
bearish names, and emails the top 5 Bullish and top 5 Bearish with the contracts behind each call.

**Stages** (each prints the read-only Robinhood calls for the next; the names depend on the scan):
1. `python3 -m research.unusual scan` - one market-wide `preview_scan` (1 call)
2. `python3 -m research.unusual chains` - expirations for the 10 shortlisted names (10 calls)
3. `python3 -m research.unusual contracts` - one page of nearest-expiry calls and puts from 7% below the price (10 calls)
4. `python3 -m research.unusual quotes` - option quotes for the 12 strikes each side nearest the money (2 calls)
5. `python3 -m research.unusual report --out /tmp/unusual_report.html` - builds the email

Every stage uses the scan's time (saved in `/tmp/unusual_now.txt`), so the shortlist cannot change between stages.

**Scan filter** (pace-adjusted: at 9:35 only ~17% of the day has traded, so the thresholds scale with the share of
the session elapsed): options volume > 2x the 10-day average, options premium >= $5M, price >= $10; then market
cap >= $2B in code.

**What each requested technical maps to:**

| Technical | How it is measured | Source |
|---|---|---|
| Volume > OI | contract volume above open interest = new positions | option quotes |
| Premium > $50K | volume x mark x 100 >= $50K per contract | option quotes |
| Relative volume | options volume / 10-day average, and stock RVOL (30-day), both pace-adjusted | scan |
| Bid / Ask | bid x size / ask x size and spread % of each unusual contract | option quotes |
| IV | ATM IV, IV rank (rich >= 80, cheap <= 20), front vs back IV (event premium) | scan + quotes |
| GEX | sum of gamma x OI x 100 x S^2 x 1% (calls +, puts -), plus call and put walls | option quotes |
| Catalyst | earnings within 7 days (or just reported), front IV > 1.1 x back IV | scan |
| Sweeps | **not available** - Robinhood quotes carry no prints or exchange routing | - |

Trade side (bought at the ask vs sold at the bid) is also unavailable, so premium can be sold as well as bought; a
call-heavy mix can be covered-call writing. The email says so.

**Score** (direction; total >= +2 Bullish, <= -2 Bearish, else Neutral):

| Factor | Rule | Points |
|---|---|---|
| Premium mix | call share of options premium >= 70% / >= 60% / <= 40% / <= 30% | +2 / +1 / -1 / -2 |
| Unusual contracts | call share of premium in contracts with volume > OI and >= $50K: >= 65% / <= 35% | +1 / -1 |
| Tape | stock change >= +1% / <= -1% | +1 / -1 |

Ranking within each side: intensity (options RVOL >= 5 -> 2, >= 3 -> 1; stock RVOL >= 2 -> 1; volume/OI >= 0.25
-> 1; premium >= $50M -> 1), then premium.

**Caveats:** nothing is tuned and nothing is validated out of sample. GEX covers only the nearest expiry's 24
contracts and assumes dealers are long calls and short puts.

First live test (2026-10-28 full-day data, run overnight): 179 names passed the scan, 145 single stocks;
Bullish MRNA, CMG, COST, XOM, V; Bearish FTNT, TSEM, RIOT, CDE (only 4 reached -2).

## Scheduled-task prompt

```
You are the UNUSUAL options-flow Research Agent. RESEARCH-ONLY: never call any order-placing, order-reviewing, cancel, exercise, alert-, scan-saving or watchlist-modifying tool (preview_scan is read-only and allowed). All calculations and the email HTML are produced by a tested Python script in the DayTrading repo - do NOT compute scores, read the raw data, or write analysis yourself.

STEP 1 - script setup (Bash, one command; it clones the public repo if it is not already present):
R=""; for d in "$PWD" /home/user/DayTrading /home/user/daytrading "$HOME/DayTrading"; do [ -d "$d/.git" ] && R="$d" && break; done; if [ -z "$R" ]; then R="$HOME/DayTrading"; GIT_TERMINAL_PROMPT=0 timeout 90 git clone -q --depth 1 --branch claude/upbeat-knuth-878qp7 https://github.com/mail11dira-ai/DayTrading.git "$R"; fi; cd "$R" && GIT_TERMINAL_PROMPT=0 timeout 60 git fetch -q origin claude/upbeat-knuth-878qp7 && git checkout -q FETCH_HEAD && test -f research/unusual.py && echo READY
If this does not print READY, skip to FALLBACK below. Run every later command from that repo directory.

Load the tools once with ToolSearch "select:mcp__Robinhood_Agentic__preview_scan,mcp__Robinhood_Agentic__get_option_chains,mcp__Robinhood_Agentic__get_option_instruments,mcp__Robinhood_Agentic__get_option_quotes".
For STEPS 2-5: each command prints one JSON line per read-only Robinhood call ({"tool": ..., "args": ...}). Make EVERY listed call with exactly those arguments, all in parallel in one message. Do not open, summarize or re-type the results (large ones are saved to files automatically - that is expected). If a call errors, retry it once. Finish each step's calls before running the next command - each step reads the previous step's results from this session's transcript.

STEP 2 - run `python3 -m research.unusual scan` and make the call.
STEP 3 - run `python3 -m research.unusual chains` and make all the calls.
STEP 4 - run `python3 -m research.unusual contracts` and make all the calls.
STEP 5 - run `python3 -m research.unusual quotes` and make all the calls.
STEP 6 - run `python3 -m research.unusual report --out /tmp/unusual_report.html`. It prints JSON with "subject", "parts", "scored" and "missing".
STEP 7 - send: `cat` each file in "parts" (in order) and concatenate them exactly into htmlBody. Send with mcp__Gmail__send_message (ToolSearch "select:mcp__Gmail__send_message"): to ["mail11dira@gmail.com"], subject = the printed subject, htmlBody = the concatenated HTML, unchanged. Send to that address only, never to anyone else.
STEP 8 - final message: one line with the subject, "sent", the "scored" count and the "missing" list. Do not commit or push anything.

If STEPS 2-6 fail after one retry (script error, empty report), use FALLBACK.

FALLBACK (only if the script cannot be used): RESEARCH-ONLY, with read-only Robinhood_Agentic tools: run preview_scan with filters optionsTotalDayVolume > 2 * optionsTotalVolumeAvg10Day (= True), optionsDayPremium() >= 5000000, tradeAllDay.price >= 10, and columns call/put premium (optionsDayPremium(callput="C"/"P")), optionsTotalVolumeAvg10Day, ivRank, fundamental.earningsYmd, fundamental.marketCap, changeFromCloseAllDayRatio(candlePeriod="1d"). Drop rows with no market cap (ETFs). Score: call share of premium >= 70% +2, >= 60% +1, <= 40% -1, <= 30% -2; stock change >= +1% +1, <= -1% -1. Total >= +2 Bullish, <= -2 Bearish. Email the top 5 of each side by premium: HTML table (stock, call, score, price, change, premium and call %, options volume vs 10-day average, IV rank, earnings date) and the note "Fixed-weight checklist, not validated out of sample; sweeps and trade side are not available from Robinhood, so premium can be sold as well as bought." Only the words Bullish (green #0a7d2c) and Bearish (red #c0392b) coloured, title "UNUSUAL Options Flow - <date> <time> CT", footer "Research only, not financial advice. No orders placed." Send with mcp__Gmail__send_message to mail11dira@gmail.com only. Do not commit or push anything.
```
