"""Session context and policy / macro events for the Super 10 email - deterministic rules plus validated, sourced events.

Session context is computed from the calendar (no model calls): monthly options expiry, VIX expiry, quad witching
and index rebalancing, month / quarter end.

Policy and macro events (Fed speakers, data releases, tariff or government actions) cannot be computed. The agent
searches for today's dated events and writes them to a JSON file; this module keeps only the items that have a
time, an impact level and an http(s) source, and renders them. Nothing is invented here.
"""
import json
from datetime import date, timedelta

IMPACTS = ("High", "Medium", "Low")


def _third_friday(year, month):
    d = date(year, month, 1)
    first_friday = d + timedelta(days=(4 - d.weekday()) % 7)
    return first_friday + timedelta(days=14)


def _last_weekday(year, month):
    d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def session_context(day):
    """Calendar flags for a trading day, most important first."""
    flags = []
    tf = _third_friday(day.year, day.month)
    if day == tf:
        if day.month in (3, 6, 9, 12):
            flags.append("Quad witching (index futures, options and stock expiry) with index rebalancing: expect closing-auction volume and whipsaw into 3:00 CT")
        else:
            flags.append("Monthly options expiry (OPEX): pinning near large strikes, faster moves after 2:00 CT")
    nxt = date(day.year + (day.month == 12), day.month % 12 + 1, 1)
    vix_exp = _third_friday(nxt.year, nxt.month) - timedelta(days=30)  # VIX expires 30 days before the next month's third Friday
    if day == vix_exp:
        flags.append("VIX expiry: volatility products settle today, so VIX can move on settlement flows")
    if day == _last_weekday(day.year, day.month):
        if day.month in (3, 6, 9, 12):
            flags.append("Quarter end: pension and fund rebalancing flows late in the session")
        else:
            flags.append("Month end: rebalancing flows late in the session")
    if day.weekday() == 0:
        flags.append("Monday: weekend news is priced at the open, so gap risk is higher")
    if day.weekday() == 4:
        flags.append("Friday: weekend headline risk; some desks reduce size into the close")
    return flags


def load_events(path, day):
    """Validated events for day from the agent's JSON file. Returns (events, dropped_count)."""
    if not path:
        return [], 0
    try:
        with open(path) as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return [], 0
    if not isinstance(raw, list):
        return [], 0
    keep, dropped = [], 0
    for e in raw:
        ok = (isinstance(e, dict) and str(e.get("date", "")) == str(day) and e.get("event")
              and str(e.get("time_ct", "")).count(":") == 1 and e.get("impact") in IMPACTS
              and str(e.get("source", "")).startswith(("https://", "http://")))
        if ok:
            keep.append({"time_ct": e["time_ct"], "event": str(e["event"])[:140], "impact": e["impact"],
                         "source": e["source"], "note": str(e.get("note", ""))[:200]})
        elif isinstance(e, dict) and str(e.get("date", "")) == str(day):
            dropped += 1  # on today but missing a time, impact or source: not shown
    return sorted(keep, key=lambda e: e["time_ct"]), dropped
