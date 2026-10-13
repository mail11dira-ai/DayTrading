"""Ticker universes for the research agents.

A ticker given as None is not available on Robinhood: it is shown as
"n/a - not on Robinhood" and excluded from averages.
"""

MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"]
MAG7_BENCHMARKS = ["SPY", "QQQ"]

AI_BENCHMARKS = ["SPY", "QQQ", "SMH", "XLU"]

# (display name, Robinhood symbol or None)
AI_SECTORS = [
    ("Memory", [
        ("L1", "Equipment", [("ASML", "ASML"), ("AMAT", "AMAT"), ("LRCX", "LRCX"),
                             ("KLAC", "KLAC"), ("TER", "TER"), ("ONTO", "ONTO")]),
        ("L2", "Memory Makers", [("MU", "MU"), ("SK Hynix", "SKHY"), ("Samsung", None),
                                 ("WDC", "WDC"), ("SNDK", "SNDK"), ("Kioxia", None)]),
        ("L3", "Packaging & Test", [("TSM", "TSM"), ("AMKR", "AMKR"), ("ASE", "ASX"),
                                    ("BESI", "BESIY"), ("DISCO", "DSCSY"), ("ASMPT", "ASMVY")]),
        ("L4", "Storage Platforms", [("PSTG", None), ("NTAP", "NTAP"), ("DELL", "DELL"),
                                     ("HPE", "HPE")]),
        ("L5", "AI Demand", [("AVGO", "AVGO"), ("AMD", "AMD")]),
    ]),
    ("AI Power Stack", [
        ("L1", "Generation", [("VST", "VST"), ("CEG", "CEG"), ("NRG", "NRG"),
                              ("NEE", "NEE"), ("DUK", "DUK"), ("SO", "SO")]),
        ("L2", "Nuclear", [("CCJ", "CCJ"), ("UEC", "UEC"), ("BWXT", "BWXT"),
                           ("LEU", "LEU"), ("SMR", "SMR"), ("OKLO", "OKLO")]),
        ("L3", "Grid", [("ETN", "ETN"), ("PWR", "PWR"), ("HUBB", "HUBB"),
                        ("GEV", "GEV"), ("ABB", "ABBNY"), ("SGRE", None)]),
        ("L4", "Power Management", [("ENB", "ENB"), ("GNRC", "GNRC"), ("CAT", "CAT"),
                                    ("CMI", "CMI"), ("NVT", "NVT"), ("VRT", "VRT")]),
        ("L5", "Demand Centers", [("ORCL", "ORCL"), ("DLR", "DLR")]),
    ]),
    ("Data Center", [
        ("L1", "Power", []),  # all covered in AI Power Stack
        ("L2", "Compute", [("INTC", "INTC"), ("ARM", "ARM")]),
        ("L3", "Networking", [("ANET", "ANET"), ("MRVL", "MRVL"), ("CRDO", "CRDO"),
                              ("CSCO", "CSCO"), ("LITE", "LITE"), ("AAOI", "AAOI")]),
        ("L4", "Cooling", [("TT", "TT"), ("MOD", "MOD"), ("CARR", "CARR"), ("JCI", "JCI")]),
        ("L5", "Operators", [("EQIX", "EQIX")]),
    ]),
]

EMPTY_LAYER_NOTE = "covered in AI Power Stack (VST, CEG, ETN, PWR, GEV, ENB)"

# Thinly traded OTC ADRs: VWAP/RVOL marked "thin".
OTC = {"BESIY", "DSCSY", "ASMVY", "ABBNY"}


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
