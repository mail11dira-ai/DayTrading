# Daily Quant Brief

Research only - no orders. Overnight-to-open brief emailed to mail11dira@gmail.com Mon-Fri at 8:00 am CT
(the scheduler places it at about 8:04), 26 minutes before the open. Model: Sonnet.

- `prompt.md` - the brief specification, v2.0 "simple, sleek, dense": 6 sections, 700-1,100 words. The research
  rules (no invented numbers, nothing stale, arithmetic recomputed) still apply but run silently: no T1/T2/T3 tags,
  missing data is dropped instead of printed as UNAVAILABLE, estimates are marked "~". The user's original v1.0
  (12 sections, 1,800-2,800 words, full provenance tags and source log) is in git history (commit 678bb2a).
- `wrapper.txt` - what the scheduled task adds in front of it: read-only tool rules, watchlist (the Super 10 list),
  a fixed email design (680px card, compact tables, only Bull/Bear words coloured) and Gmail delivery to
  mail11dira@gmail.com only; subject carries the regime and SPY bias.

Scheduled task: trig_01UYeZ6Dm4douirodKhcPTG8 "Daily Quant Brief (8:00 am)". Its prompt = wrapper.txt + prompt.md.

Unlike the other agents there is no Python script: the model gathers the data (Robinhood + web search) and writes
the brief itself, so numbers are not computed by tested code; the silent research rules are the check on that. Not validated out of sample.

**Connectors:** Robinhood_Agentic and Gmail were attached by the user in the claude.ai task settings (2026-10-30).
