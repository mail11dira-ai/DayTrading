"""Node X3: rank tickers by weighted stance. Code only.

score(ticker) = sum over labels of sign(stance) * confidence, where each handle's contribution
to a ticker is capped at 1.0 so one prolific account cannot dominate. Consensus (distinct handles
on the same side) breaks ties, then mention count.
"""
from __future__ import annotations

from collections import defaultdict

from xers.config import NON_TRADEABLE, TOP_N
from xers.sentiment import STANCES


def rank(labels: list[dict], tweets: list[dict], top_n: int = TOP_N) -> dict:
    handle_of = {t["id"]: t["handle"] for t in tweets}
    per = defaultdict(lambda: defaultdict(float))          # ticker -> handle -> raw score
    support = defaultdict(list)
    for lb in labels:
        tk = lb["ticker"]
        if tk in NON_TRADEABLE or lb["stance"] == "neutral":
            continue
        h = handle_of[lb["tweet_id"]]
        per[tk][h] += STANCES[lb["stance"]] * lb["confidence"]
        support[tk].append(lb)

    rows = []
    for tk, by_handle in per.items():
        capped = {h: max(-1.0, min(1.0, v)) for h, v in by_handle.items()}
        score = sum(capped.values())
        side = 1 if score > 0 else -1
        rows.append({
            "ticker": tk,
            "score": round(score, 3),
            "handles_agree": sorted(h for h, v in capped.items() if v * side > 0),
            "handles_disagree": sorted(h for h, v in capped.items() if v * side < 0),
            "mentions": len(support[tk]),
            "tweet_ids": sorted({lb["tweet_id"] for lb in support[tk]}),
            "reasons": [lb.get("reason", "") for lb in support[tk]][:5],
        })

    key = lambda r: (abs(r["score"]), len(r["handles_agree"]), r["mentions"])
    bull = sorted((r for r in rows if r["score"] > 0), key=key, reverse=True)[:top_n]
    bear = sorted((r for r in rows if r["score"] < 0), key=key, reverse=True)[:top_n]
    return {"bullish": bull, "bearish": bear}
