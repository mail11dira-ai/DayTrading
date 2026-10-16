"""Ticker universes for the research agents.

A ticker given as None is not available on Robinhood: it is shown as
"n/a - not on Robinhood" and excluded from averages.
"""

MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"]
MAG7_BENCHMARKS = ["SPY", "QQQ"]

AI_BENCHMARKS = ["SPY", "QQQ", "SMH", "XLU"]

# (display name, Robinhood symbol or None)
# 2026-10-16: trimmed to liquid names (20-day avg dollar volume >= ~$1B) and added
# the top 5 neo-clouds by dollar volume. Layers left empty by the trim are dropped;
# layer codes keep their original numbers so L1 = upstream, L5 = downstream.
AI_SECTORS = [
    ("Memory", [
        ("L1", "Equipment", [("ASML", "ASML"), ("AMAT", "AMAT"), ("LRCX", "LRCX"), ("KLAC", "KLAC")]),
        ("L2", "Memory Makers", [("MU", "MU"), ("SK Hynix", "SKHY"), ("WDC", "WDC"), ("SNDK", "SNDK")]),
        ("L3", "Packaging & Test", [("TSM", "TSM")]),
        ("L4", "Storage Platforms", [("DELL", "DELL"), ("HPE", "HPE")]),
        ("L5", "AI Demand", [("AVGO", "AVGO"), ("AMD", "AMD")]),
    ]),
    ("AI Power Stack", [
        ("L1", "Generation", [("VST", "VST"), ("CEG", "CEG")]),
        ("L3", "Grid", [("GEV", "GEV")]),
        ("L4", "Power Management", [("CAT", "CAT"), ("VRT", "VRT")]),
        ("L5", "Demand Centers", [("ORCL", "ORCL")]),
    ]),
    ("Data Center", [
        ("L2", "Compute", [("INTC", "INTC"), ("ARM", "ARM")]),
        ("L3", "Networking", [("ANET", "ANET"), ("MRVL", "MRVL"), ("CRDO", "CRDO"),
                              ("CSCO", "CSCO"), ("LITE", "LITE"), ("AAOI", "AAOI")]),
    ]),
    ("Neo-Cloud", [
        ("L1", "GPU Clouds", [("CRWV", "CRWV"), ("NBIS", "NBIS")]),
        ("L2", "AI Hosting / HPC", [("IREN", "IREN"), ("CIFR", "CIFR"), ("APLD", "APLD")]),
    ]),
]

EMPTY_LAYER_NOTE = "covered in another ecosystem"

# Thinly traded OTC ADRs: VWAP/RVOL marked "thin". (All removed in the 2026-10-16 trim.)
OTC = set()


def ai_symbols():
    out = []
    for _, layers in AI_SECTORS:
        for _, _, tickers in layers:
            out += [sym for _, sym in tickers if sym]
    assert len(out) == len(set(out)), "AI Sectors universe has duplicates"
    assert not set(out) & set(MAG7), "AI Sectors universe must exclude MAG 7"
    return out


def symbols(agent):
    if agent == "mag7":
        return MAG7, MAG7_BENCHMARKS
    if agent == "aisectors":
        return ai_symbols(), AI_BENCHMARKS
    raise ValueError(f"unknown agent {agent!r}")
