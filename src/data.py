"""Node N1: turn raw Robinhood MCP historicals JSON into clean, validated 5-minute bars.

Raw files are saved MCP responses (`get_equity_historicals`), one symbol per file.
Usage: python -m src.data data/raw data/bars_5m.csv.gz
"""
from pathlib import Path
import json
import sys

import pandas as pd

TZ = "America/New_York"
INTERVAL = "5minute"
COLUMNS = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]


def parse_raw(path: Path, interval: str = INTERVAL) -> pd.DataFrame:
    """Parse one raw MCP response. Drops interpolated (gap-fill) bars and other intervals."""
    payload = json.loads(Path(path).read_text())
    rows = []
    for result in payload["data"]["results"]:
        if result.get("interval") != interval:
            continue
        for bar in result["bars"]:
            if bar.get("interpolated"):
                continue
            rows.append({
                "symbol": result["symbol"],
                "timestamp": bar["begins_at"],
                "open": float(bar["open_price"]),
                "high": float(bar["high_price"]),
                "low": float(bar["low_price"]),
                "close": float(bar["close_price"]),
                "volume": int(bar["volume"]),
            })
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(TZ)
    return df


def build(raw_dir: Path) -> pd.DataFrame:
    frames = [parse_raw(p) for p in sorted(Path(raw_dir).glob("*.txt"))]
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(["symbol", "timestamp"]).sort_values(["symbol", "timestamp"])
    return df.reset_index(drop=True)


def validate(df: pd.DataFrame, max_missing_sessions: int = 1) -> list[str]:
    """Return a list of problems; empty means the gate passes."""
    problems = []
    if df[["open", "high", "low", "close", "volume"]].isna().any().any():
        problems.append("NaN values present")
    if str(df["timestamp"].dt.tz) != TZ:
        problems.append(f"timestamps not in {TZ}")
    bad_ohlc = (df["high"] < df[["open", "close", "low"]].max(axis=1)) | (
        df["low"] > df[["open", "close", "high"]].min(axis=1))
    if bad_ohlc.any():
        problems.append(f"{int(bad_ohlc.sum())} bars with inconsistent OHLC")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        problems.append("non-positive prices")
    t = df["timestamp"].dt.time
    if ((t < pd.Timestamp("09:30").time()) | (t > pd.Timestamp("15:55").time())).any():
        problems.append("bars outside regular trading hours")

    all_sessions = set(df["timestamp"].dt.date)
    for sym, g in df.groupby("symbol"):
        if not g["timestamp"].is_monotonic_increasing:
            problems.append(f"{sym}: timestamps not monotonic")
        missing = all_sessions - set(g["timestamp"].dt.date)
        if len(missing) > max_missing_sessions:
            problems.append(f"{sym}: missing {len(missing)} sessions")
    return problems


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("symbol")
    return pd.DataFrame({
        "bars": g.size(),
        "sessions": g["timestamp"].agg(lambda s: s.dt.date.nunique()),
        "first": g["timestamp"].min(),
        "last": g["timestamp"].max(),
    })


def load(path: str | Path = "data/bars_5m.csv.gz") -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(TZ)
    return df


if __name__ == "__main__":
    raw_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
    df = build(raw_dir)
    print(coverage(df).to_string())
    problems = validate(df)
    print("PROBLEMS:" if problems else "VALIDATION: pass", *problems, sep="\n  ")
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows to {out}")
    sys.exit(1 if problems else 0)
