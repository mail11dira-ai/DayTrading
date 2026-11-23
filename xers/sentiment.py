"""Node X2: per-(tweet, ticker) stance labels.

The primary labels are written by the model (judgment) to `labels.json`; code validates them.
A keyword lexicon provides a fallback so the pipeline still runs without model labels.

Label schema: {"tweet_id": str, "ticker": str, "stance": "bullish"|"bearish"|"neutral",
               "confidence": float 0..1, "reason": str}
"""
from __future__ import annotations

import re

STANCES = {"bullish": 1, "bearish": -1, "neutral": 0}

BULL = ["bullish", "calls", "call sweep", "call buying", "breakout", "upgrade", "upgraded", "beat",
        "beats", "raises guidance", "raised guidance", "buyback", "insider buy", "insider buying",
        "bought", "long", "new high", "all-time high", "price target raised", "pt raised", "squeeze",
        "outperform", "strong buy", "surges", "soars", "jumps", "rallies", "approval", "approved"]
BEAR = ["bearish", "puts", "put sweep", "put buying", "breakdown", "downgrade", "downgraded", "miss",
        "misses", "cuts guidance", "lowered guidance", "insider sell", "insider selling", "sold",
        "short", "new low", "price target cut", "pt cut", "underperform", "sell rating", "plunges",
        "tumbles", "falls", "drops", "sinks", "probe", "investigation", "lawsuit", "recall", "offering"]


def _hits(text: str, words: list[str]) -> int:
    t = text.lower()
    return sum(1 for w in words if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t))


def lexicon_labels(tweets: list[dict]) -> list[dict]:
    """Same stance for every ticker in a tweet; confidence grows with keyword margin."""
    out = []
    for t in tweets:
        b, s = _hits(t["text"], BULL), _hits(t["text"], BEAR)
        stance = "bullish" if b > s else "bearish" if s > b else "neutral"
        conf = 0.0 if stance == "neutral" else min(1.0, 0.4 + 0.2 * abs(b - s))
        for tk in t["cashtags"]:
            out.append({"tweet_id": t["id"], "ticker": tk, "stance": stance,
                        "confidence": round(conf, 2), "reason": f"lexicon bull={b} bear={s}"})
    return out


def validate(labels: list[dict], tweets: list[dict]) -> list[str]:
    """Problems with model labels; empty list means they can be used."""
    by_id = {t["id"]: t for t in tweets}
    problems = []
    for i, lb in enumerate(labels):
        where = f"label {i} ({lb.get('tweet_id')}/{lb.get('ticker')})"
        t = by_id.get(str(lb.get("tweet_id")))
        if t is None:
            problems.append(f"{where}: unknown tweet_id")
            continue
        if lb.get("ticker") not in t["cashtags"]:
            problems.append(f"{where}: ticker is not a cashtag in that tweet")
        if lb.get("stance") not in STANCES:
            problems.append(f"{where}: stance must be one of {sorted(STANCES)}")
        c = lb.get("confidence")
        if not isinstance(c, (int, float)) or not 0 <= c <= 1:
            problems.append(f"{where}: confidence must be a number in [0, 1]")
    return problems
