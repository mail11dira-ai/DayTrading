"""CLI for the Xers pipeline. See .claude/skills/xers-premarket/SKILL.md for the full run.

  python -m xers.run fetch   [--date D] [--paste FILE]   # X1: tweets.json
  python -m xers.run prepare [--date D]                  # X2: labeling_input.md + lexicon fallback
  python -m xers.run rank    [--date D]                  # X3: ranking.json (+ tickers needing bars)
  python -m xers.run report  [--date D] [--sample]       # X4+X5: reports/xers/D.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from xers import levels as lvmod
from xers import rank as rankmod
from xers import report as reportmod
from xers import sentiment, tweets as tw
from xers.config import ET, REPORT_ROOT, day_dir, window


def _read(p: Path):
    return json.loads(p.read_text())


def _write(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, default=str))


def cmd_fetch(d: date, paste: str | None):
    start, end = window(d)
    out = day_dir(d)
    if paste:
        posts, errors = tw.load_paste(Path(paste), default_time=start.isoformat()), {}
    else:
        posts, errors = tw.fetch_api(start, end)
    kept = tw.in_window(posts, start, end)
    _write(out / "tweets.json", kept)
    _write(out / "fetch_errors.json", errors)
    print(f"{len(kept)} posts in window ({len(posts) - len(kept)} outside) -> {out / 'tweets.json'}")
    for h, e in errors.items():
        print(f"  fetch error @{h}: {e}")
    return 0 if kept or not errors else 1


def cmd_prepare(d: date):
    out = day_dir(d)
    posts = _read(out / "tweets.json")
    _write(out / "labels_lexicon.json", sentiment.lexicon_labels(posts))
    lines = ["# Posts to label", "",
             "For every cashtag in every post, write one label to labels.json:",
             '{"tweet_id", "ticker", "stance": bullish|bearish|neutral, "confidence": 0..1, "reason"}', ""]
    for t in posts:
        if t["cashtags"]:
            lines.append(f"- id={t['id']} @{t['handle']} {t['created_at']} tickers={','.join(t['cashtags'])}")
            lines.append(f"  {' '.join(t['text'].split())}")
    (out / "labeling_input.md").write_text("\n".join(lines))
    n = sum(len(t["cashtags"]) for t in posts)
    print(f"{n} (post, ticker) pairs to label -> {out / 'labeling_input.md'}")
    return 0


def _labels(out: Path, posts: list[dict]) -> tuple[list[dict], str]:
    p = out / "labels.json"
    if p.exists():
        labels = _read(p)
        problems = sentiment.validate(labels, posts)
        if not problems:
            return labels, "model (validated)"
        print("labels.json rejected, falling back to lexicon:", *problems[:10], sep="\n  ")
    return _read(out / "labels_lexicon.json"), "keyword lexicon (fallback)"


def cmd_rank(d: date):
    out = day_dir(d)
    posts = _read(out / "tweets.json")
    labels, source = _labels(out, posts)
    ranking = rankmod.rank(labels, posts)
    ranking["label_source"] = source
    _write(out / "ranking.json", ranking)
    tickers = [r["ticker"] for side in ("bullish", "bearish") for r in ranking[side]]
    print(f"labels: {source}")
    print("bullish:", [r["ticker"] for r in ranking["bullish"]])
    print("bearish:", [r["ticker"] for r in ranking["bearish"]])
    print("NEED_BARS:", ",".join(tickers))
    return 0


def cmd_report(d: date, sample: bool):
    out = day_dir(d)
    posts, ranking = _read(out / "tweets.json"), _read(out / "ranking.json")
    bars = lvmod.load_bars(sorted((out / "bars").glob("*")))
    levels, plans = {}, {}
    for side in ("bullish", "bearish"):
        for r in ranking[side]:
            sym_bars = bars[bars["symbol"] == r["ticker"]]
            lv = lvmod.compute_levels(sym_bars, d) if not sym_bars.empty else None
            levels[r["ticker"]] = lv
            plans[r["ticker"]] = lvmod.plan(lv, side) if lv else None
    start, end = window(d)
    errors = _read(out / "fetch_errors.json") if (out / "fetch_errors.json").exists() else {}
    text = reportmod.build(d, start, end, posts, ranking, levels, plans,
                           ranking.get("label_source", "?"), errors, sample=sample)
    path = REPORT_ROOT / f"{d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    missing = [t for t, v in levels.items() if v is None]
    print(f"wrote {path}" + (f" (no bars: {', '.join(missing)})" if missing else ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["fetch", "prepare", "rank", "report"])
    ap.add_argument("--date", default=datetime.now(ET).date().isoformat())
    ap.add_argument("--paste")
    ap.add_argument("--sample", action="store_true")
    a = ap.parse_args(argv)
    d = date.fromisoformat(a.date)
    if a.stage == "fetch":
        return cmd_fetch(d, a.paste)
    if a.stage == "prepare":
        return cmd_prepare(d)
    if a.stage == "rank":
        return cmd_rank(d)
    return cmd_report(d, a.sample)


if __name__ == "__main__":
    sys.exit(main())
