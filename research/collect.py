"""Collect Robinhood MCP tool results without the model re-typing them.

Sources (any combination):
  * the Claude Code session transcript (~/.claude/projects/*/<session>.jsonl):
    inline tool results, and results the harness saved to tool-results/*.txt;
  * a directory of raw JSON files (tests / replays).

Results are classified by shape, so tool names are not needed.
"""
import glob
import json
import os
import re

SAVED_RE = re.compile(r"saved to (\S+\.txt)")


class Dataset:
    def __init__(self):
        self.quotes = {}        # sym -> {"quote": {...}, "close": {...}}
        self.bars = {}          # (sym, interval) -> {begins_at: bar}
        self.earnings = []      # [{"symbol", "report": {"date", "timing"}}]
        self.ratings = {}       # sym -> ratings dict
        self.fundamentals = {}  # sym -> dict
        self.indexes = {}       # index symbol (e.g. VIX) -> level
        self.sources = 0

    def add(self, payload):
        if not isinstance(payload, dict):
            return
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("quotes"), list):  # get_index_quotes
            for q in data["quotes"]:
                try:
                    self.indexes[q["symbol"]] = float(q["value"])
                except (KeyError, TypeError, ValueError):
                    pass
            self.sources += 1
            return
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list) or not results:
            return
        self.sources += 1
        for r in results:
            if not isinstance(r, dict):
                continue
            if "bars" in r and "symbol" in r:
                key = (r["symbol"], r.get("interval", "?"))
                store = self.bars.setdefault(key, {})
                for b in r["bars"] or []:
                    if b.get("interpolated"):
                        continue
                    store[b["begins_at"]] = b
            elif "quote" in r and isinstance(r["quote"], dict):
                if r["quote"].get("symbol"):  # equity quote (option quotes carry instrument_id instead)
                    self.quotes[r["quote"]["symbol"]] = r
            elif "ratings" in r and "symbol" in r:
                if r["ratings"]:
                    self.ratings[r["symbol"]] = r["ratings"]
            elif "report" in r and "symbol" in r:
                self.earnings.append(r)
            elif "pe_ratio" in r and "symbol" in r:
                self.fundamentals[r["symbol"]] = r

    def series(self, sym, interval):
        store = self.bars.get((sym, interval), {})
        return [store[k] for k in sorted(store)]


def _parse_text(text):
    if not isinstance(text, str):
        return None
    m = SAVED_RE.search(text) if text.startswith("Error: result") else None
    if m and os.path.exists(m.group(1)):
        with open(m.group(1)) as f:
            text = f.read()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def latest_transcript():
    files = glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def load_transcript(path, ds):
    robinhood_ids = set()
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use" and "Robinhood" in c.get("name", ""):
                    robinhood_ids.add(c.get("id"))
                elif c.get("type") == "tool_result" and c.get("tool_use_id") in robinhood_ids:
                    body = c.get("content")
                    if isinstance(body, list):
                        body = "".join(x.get("text", "") for x in body if isinstance(x, dict))
                    ds.add(_parse_text(body))
    return ds


def load_dir(path, ds):
    for fn in sorted(glob.glob(os.path.join(path, "*"))):
        if os.path.isfile(fn):
            with open(fn) as f:
                ds.add(_parse_text(f.read()))
    return ds
