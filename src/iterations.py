"""Node N5/N6 registry: each iteration changes ONE thing vs. the previous accepted strategy.

Usage: python -m src.iterations <iter_name> [--test]
"""
import sys
from pathlib import Path

from src.evaluate import report
from src.strategies.orb import ORB

ITERATIONS = {
    "iter_1": dict(
        notes=("**Change:** long-only (`allow_short=False`) vs. baseline ORB.\n\n"
               "**Hypothesis:** in the train window longs made +$1,200 and shorts lost -$1,730 "
               "(410 trades); downside breakouts in a rising market are mostly noise."),
        strategies={"ORB 30m (baseline)": ORB(), "ORB 30m long-only": ORB(allow_short=False)},
    ),
    "iter_2": dict(
        notes=("**Change:** opening range 60 min (`range_bars=12`) vs. baseline 30 min. "
               "iter_1 (long-only) was rejected, so this changes the baseline, not iter_1.\n\n"
               "**Hypothesis:** a longer range filters false breakouts.\n\n"
               "**Train-only tuning** (test untouched): 15m Sharpe -1.85, 30m -0.48, "
               "60m -0.04, 90m -0.89. 60m chosen."),
        strategies={"ORB 30m (baseline)": ORB(), "ORB 60m": ORB(range_bars=12)},
    ),
    "iter_3": dict(
        notes=("**Change:** relative-volume filter (`min_rvol=1.0`, 10-session lookback) on baseline ORB 30m.\n\n"
               "**Hypothesis:** breakouts only follow through in stocks trading above normal volume "
               "(\"stocks in play\").\n\n"
               "**Train-only tuning** (test untouched): rvol off Sharpe -0.48, 1.0 → 1.55, 1.5 → 0.88, "
               "2.0 → -1.47, 3.0 → -1.10. 1.0 chosen.\n\n"
               "**Confound check:** the filter needs 10 sessions of history, so it skips the first 10 "
               "sessions of each window. Baseline on train sessions 11-112 alone: Sharpe -0.48 "
               "(unchanged), so warm-up does not explain the gain. In the test window the filter can "
               "only trade the last 38 of 48 sessions."),
        strategies={"ORB 30m (baseline)": ORB(), "ORB 30m + RVOL>=1.0": ORB(min_rvol=1.0)},
    ),
}

if __name__ == "__main__":
    name = sys.argv[1]
    it = ITERATIONS[name]
    text = report(name, it["strategies"], include_test="--test" in sys.argv, notes=it["notes"])
    Path(f"backtests/{name}.md").write_text(text)
    print(text)
