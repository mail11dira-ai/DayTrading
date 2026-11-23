"""Node X1: collect overnight posts. Code only.

Two sources, same output (`tweets.json`, a list of Tweet dicts):
- X API v2 (`fetch_api`): needs a bearer token. Either set X_BEARER_TOKEN, or save a network
  secret for api.x.com on the environment (the proxy injects it; a dummy token is sent).
- Manual paste (`load_paste`): `paste.txt` with one post per block, first line `@handle`,
  optional second line `time: 2026-11-24 07:42` (ET), then the text. Blocks separated by a blank line.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from xers.config import ET, HANDLES

API = "https://api.x.com/2"
CASHTAG = re.compile(r"\$([A-Za-z]{1,5}(?:\.[A-Za-z])?)(?![A-Za-z])")


def cashtags(text: str) -> list[str]:
    """Unique uppercase cashtags in order of appearance ($nvda -> NVDA, $BRK.B -> BRK.B)."""
    seen = []
    for m in CASHTAG.findall(text):
        t = m.upper()
        if t not in seen:
            seen.append(t)
    return seen


def make_tweet(tid: str, handle: str, created_at: str, text: str, url: str = "", **metrics) -> dict:
    return {"id": str(tid), "handle": handle.lstrip("@"), "created_at": created_at, "text": text,
            "cashtags": cashtags(text), "url": url, **metrics}


# ---------- X API ----------

def _get(path: str, params: dict, token: str) -> dict:
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "User-Agent": "xers-stocks-analysis"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_api(start: datetime, end: datetime, handles=HANDLES, token: str | None = None,
              get=_get) -> tuple[list[dict], dict]:
    """Fetch original posts and quotes (no retweets/replies) for each handle in [start, end).
    Returns (tweets, errors_by_handle)."""
    token = token or os.environ.get("X_BEARER_TOKEN") or "proxy-injected"
    iso = lambda dt: dt.astimezone(ET).isoformat(timespec="seconds")
    tweets, errors = [], {}
    for handle in handles:
        try:
            uid = get(f"/users/by/username/{handle}", {}, token)["data"]["id"]
            params = {"start_time": iso(start), "end_time": iso(end), "max_results": 100,
                      "exclude": "retweets,replies", "tweet.fields": "created_at,public_metrics"}
            while True:
                page = get(f"/users/{uid}/tweets", params, token)
                for t in page.get("data", []):
                    m = t.get("public_metrics", {})
                    tweets.append(make_tweet(t["id"], handle, t["created_at"], t["text"],
                                             url=f"https://x.com/{handle}/status/{t['id']}",
                                             likes=m.get("like_count", 0),
                                             reposts=m.get("retweet_count", 0)))
                nxt = page.get("meta", {}).get("next_token")
                if not nxt:
                    break
                params["pagination_token"] = nxt
        except Exception as e:  # one handle failing must not lose the others
            errors[handle] = f"{type(e).__name__}: {e}"
    return tweets, errors


# ---------- manual paste ----------

def load_paste(path: Path, default_time: str) -> list[dict]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", Path(path).read_text()) if b.strip()]
    out = []
    for i, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if not lines[0].startswith("@"):
            raise ValueError(f"block {i}: first line must be @handle, got {lines[0]!r}")
        handle, body, created = lines[0].split()[0], lines[1:], default_time
        if body and body[0].lower().startswith("time:"):
            local = datetime.fromisoformat(body[0].split(":", 1)[1].strip()).replace(tzinfo=ET)
            created, body = local.isoformat(), body[1:]
        out.append(make_tweet(f"paste-{i}", handle, created, "\n".join(body).strip()))
    return out


def in_window(tweets: list[dict], start: datetime, end: datetime) -> list[dict]:
    keep = []
    for t in tweets:
        ts = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
        if start <= ts < end:
            keep.append(t)
    return keep
