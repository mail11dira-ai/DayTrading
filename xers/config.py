"""Settings for the Xers agent. Edit HANDLES to change who is followed."""
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

HANDLES = [
    "wallstengine",
    "insiderhawk",
    "stocksavvyshay",
    "stockmktnewz",
    "AIStockSavvy",
    "bullflowIO",
    "quantdata",
    "unusual_whales",
]

# Cashtags that are not tradeable single stocks/ETFs for this plan (indexes, crypto, FX).
NON_TRADEABLE = {"SPX", "NDX", "DJI", "DJIA", "VIX", "RUT", "COMP", "BTC", "ETH", "SOL",
                 "XRP", "DOGE", "USD", "EUR", "JPY", "DXY"}

TOP_N = 5
WINDOW_START = time(16, 0)        # previous session close (ET)
DEFAULT_RUN_TIME = time(9, 15)    # pre-market cutoff (ET)

DATA_ROOT = Path("data/xers")
REPORT_ROOT = Path("reports/xers")


def previous_trading_day(d: date) -> date:
    """Previous weekday. Exchange holidays are not modelled (see README)."""
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def window(trade_date: date, cutoff: time = DEFAULT_RUN_TIME) -> tuple[datetime, datetime]:
    """Overnight window: previous trading day 16:00 ET -> trade_date cutoff ET."""
    start = datetime.combine(previous_trading_day(trade_date), WINDOW_START, ET)
    end = datetime.combine(trade_date, cutoff, ET)
    return start, end


def day_dir(trade_date: date) -> Path:
    return DATA_ROOT / trade_date.isoformat()
