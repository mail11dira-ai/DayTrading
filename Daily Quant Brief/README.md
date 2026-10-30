# Daily Quant Brief

Research only - no orders. Overnight-to-open brief emailed to mail11dira@gmail.com Mon-Fri at 8:00 am CT
(the scheduler places it at about 8:04), 26 minutes before the open. Model: Sonnet.

- `prompt.md` - the brief specification (v1.0, as written by the user): role, data provenance tiers T1/T2/T3 and
  hard gates, tool sequence, firm universe, conviction score, the 12 output sections and the final self-check.
- `wrapper.txt` - what the scheduled task adds in front of it: read-only tool rules, watchlist (the Super 10 list),
  Unusual Whales not connected (T3), and email delivery (HTML tables, only Bull/Bear words coloured, Gmail to
  mail11dira@gmail.com only).

Scheduled task: trig_01UYeZ6Dm4douirodKhcPTG8 "Daily Quant Brief (8:00 am)". Its prompt = wrapper.txt + prompt.md.

Unlike the other agents there is no Python script: the model gathers the data (Robinhood + web search) and writes
the brief itself, so numbers are not computed by tested code. The provenance tags and the Data Gaps section are the
check on that. Not validated out of sample.

**Connectors:** the task was created without Robinhood or Gmail (the API cannot attach them in this organization).
Add both in the claude.ai scheduled-task settings, or the run has no market data and cannot send the email
(it then writes the brief into its final message).
