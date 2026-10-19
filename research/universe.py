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


# Modern AI Sectors agent: 11 sectors from the user's sector map + Neo-Cloud.
# (number, sector, subtitle, [(ETF, description)], [leader stocks]). Symbols not on
# Robinhood are listed in NOT_ON_ROBINHOOD. Duplicates keep their first listing and MAG 7
# stocks are excluded (the MAG 7 agent covers them); modern_layout() records both as notes.
MODERN_BENCHMARKS = ["SPY", "QQQ"]
MODERN = [
    ("01", "Semiconductors / Memory", "Chips | Memory | Broad Semis",
     [("SMH", "Semiconductors"), ("DRAM", "Memory"), ("SOXX", "Semis (broad)"), ("XSD", "Semis (small caps)")],
     ["NVDA", "AMD", "AVGO", "MU", "SNDK", "INTC"]),
    ("02", "AI Infrastructure / Data Centers", "Data Centers | Cloud | AI Infrastructure",
     [("DTCR", "Data Centers"), ("PSI", "Infrastructure"), ("PSTG", "Compute Infra")],
     ["DELL", "SMCI", "VRT", "ANET"]),
    ("03", "Software / Cybersecurity", "Software | Cyber | Cloud",
     [("IGV", "Software"), ("CIBR", "Cybersecurity"), ("HACK", "Cyber (broad)"), ("SKYY", "Cloud Software")],
     ["PLTR", "CRWD", "PANW", "FTNT", "NET"]),
    ("04", "Power / Grid / Nuclear", "Grid | Electrical | Nuclear | Industrials",
     [("GRID", "Grid / Electrical"), ("XLI", "Industrials"), ("NLR", "Nuclear"), ("PAVE", "Infrastructure"),
      ("URA", "Uranium (nuclear)")],
     ["GEV", "CEG", "ETN", "VRT", "OKLO"]),
    ("05", "Crypto / Fintech", "Fintech | Blockchain | Digital Assets",
     [("ARKF", "Fintech"), ("WGMI", "Digital Assets"), ("BLOK", "Blockchain"), ("BITO", "Bitcoin"),
      ("IBIT", "Bitcoin (spot)")],
     ["HOOD", "COIN", "CRCL", "MSTR"]),
    ("06", "Space / Defense", "Space | Aerospace | Defense",
     [("ARKX", "Space & Defense"), ("ITA", "Aerospace & Defense"), ("UFO", "Aerospace (broad)"),
      ("XAR", "Defense (broad)")],
     ["ASTS", "RKLB", "LMT", "RTX", "BA"]),
    ("07", "Quantum", "Quantum Computing | Next Gen Tech",
     [("QTUM", "Quantum Computing")],
     ["IONQ", "RGTI", "QBTS", "QUBT"]),
    ("08", "Robotics / Automation", "Robotics | Automation | AI Physical",
     [("BOTZ", "Robotics"), ("ARKQ", "AI & Robotics")],
     ["TSLA", "PLTR", "ACHR", "TER"]),
    ("09", "Real Assets / Resources", "Gold | Silver | Copper | Critical Minerals",
     [("GLD", "Gold"), ("SLV", "Silver"), ("COPX", "Copper"), ("REMX", "Critical Minerals")],
     ["FCX", "TECK", "SCCO", "MP", "ALB"]),
    ("10", "Economy / Risk", "Small Caps | Financials | Energy | Travel",
     [("IWM", "Small Caps"), ("XLF", "Financials"), ("XLE", "Energy"), ("JETS", "Airlines / Travel")],
     ["IWM", "XLF", "XLE", "JETS"]),  # SPY / QQQ (context) are the benchmarks in the snapshot
    ("11", "Health / Biotech", "Biotech | Healthcare | Genomics",
     [("XBI", "Biotech"), ("XLV", "Healthcare"), ("IBB", "Biotech (broad)"), ("ARKG", "Genomics")],
     ["VRTX", "LLY", "MRNA", "ABBV"]),
    ("12", "Neo-Cloud", "GPU Clouds | AI Hosting",
     [],
     ["NBIS", "CRWV", "IREN"]),
    # 13-19 added 2026-10-19: high-volume day-trading groups missing from the map (all passed the screen below)
    ("13", "Leveraged / Volatility", "3x Nasdaq | 3x Semis | 3x Small Caps | VIX",
     [("TQQQ", "3x Nasdaq 100"), ("SQQQ", "-3x Nasdaq 100"), ("SOXL", "3x Semis"), ("SOXS", "-3x Semis"),
      ("TNA", "3x Small Caps"), ("UVXY", "1.5x VIX futures")],
     []),
    ("14", "Consumer / Internet", "E-commerce | Streaming | Social | Mobility",
     [("XLY", "Consumer Discretionary"), ("XLC", "Communication Services")],
     ["SHOP", "NFLX", "UBER", "RDDT", "CVNA"]),
    ("15", "China Tech", "China Internet | Large Caps",
     [("KWEB", "China Internet"), ("FXI", "China Large Caps")],
     ["BABA", "BIDU"]),
    ("16", "Banks / Lending", "Regional Banks | Investment Banks | Consumer Lending",
     [("KRE", "Regional Banks")],
     ["GS", "SOFI", "AFRM"]),
    ("17", "Travel / Airlines / Cruise", "Airlines | Cruise Lines",
     [],
     ["UAL", "DAL", "AAL", "CCL", "RCL"]),
    ("18", "Gold & Silver Miners", "Gold Miners | Junior Miners | Silver",
     [("GDX", "Gold Miners"), ("GDXJ", "Junior Gold Miners")],
     ["NEM", "AEM", "CDE", "HL"]),
    ("19", "Housing / Homebuilders", "Homebuilders | Rate-sensitive",
     [("ITB", "Home Construction"), ("XHB", "Homebuilders")],
     ["DHI", "LEN", "PHM"]),
]
NOT_ON_ROBINHOOD = {"PSTG"}

# 2026-10-19 day-trading screen (20-day averages from Robinhood bars). Kept: ETFs >= $150M/day;
# stocks >= $200M/day, price >= $5 and daily ATR >= 2.5% of price. Removed names stay in MODERN
# (the user's map) and are listed in each sector's notes.
DAYTRADE_REMOVED = {
    # ETFs below $150M/day: wide spreads, thin 5-minute bars
    **{e: "low volume" for e in ("ARKF", "UFO", "ARKQ", "ARKX", "BLOK", "DTCR", "BOTZ", "WGMI", "SKYY", "NLR",
                                 "HACK", "REMX", "QTUM", "PSI", "XSD", "PAVE", "XAR", "GRID", "JETS", "URA")},
    "QUBT": "low volume", "TECK": "low volume", "SCCO": "low volume",
    "ACHR": "price < $5",
    "LMT": "low range, ATR < 2.5%", "RTX": "low range, ATR < 2.5%", "ABBV": "low range, ATR < 2.5%",
    "PSTG": "not on Robinhood",
}
# Inverse / volatility products rise when the market falls: shown in their sector table, but kept out of
# sector averages and the weekend checklist (they would read as false "strength").
INVERSE = {"SQQQ", "SOXS", "UVXY"}
MODERN_NOTES = {"13": "SQQQ, SOXS and UVXY are inverse / volatility hedges: shown here, excluded from sector "
                      "averages and the weekend checklist",
                "02": "IGV (Software - AI infra) and CIBR (Cyber - AI exposure) are shown once, in 03"}


def modern_layout():
    """Sectors after de-duplication: list of dicts
    {num, name, sub, members: [(sym, kind, desc)], notes: [str]}; kind is 'ETF', 'Stock' or 'n/a'."""
    seen, out = {}, []
    for num, name, sub, etfs, leaders in MODERN:
        members, notes, dup = [], [], []
        cut = list(dict.fromkeys(x for x in [e for e, _ in etfs] + leaders if x in DAYTRADE_REMOVED and x not in seen))
        for sym, desc in etfs:
            if sym in DAYTRADE_REMOVED:
                seen.setdefault(sym, num)
                continue
            if sym in seen:
                dup.append(f"{sym} (in {seen[sym]})")
                continue
            seen[sym] = num
            members.append((sym, "n/a" if sym in NOT_ON_ROBINHOOD else "ETF", desc))
        mag = []
        for sym in leaders:
            if sym in DAYTRADE_REMOVED:
                seen.setdefault(sym, num)
                continue
            if sym in MAG7:
                mag.append(sym)
            elif sym in seen:
                if seen[sym] != num:
                    dup.append(f"{sym} (in {seen[sym]})")
            else:
                seen[sym] = num
                members.append((sym, "Stock", ""))
        if mag:
            notes.append(f"{', '.join(mag)}: covered by the MAG 7 agent")
        if dup:
            notes.append("shown once: " + ", ".join(dup))
        if cut:
            by = {}
            for x in cut:
                by.setdefault(DAYTRADE_REMOVED[x], []).append(x)
            notes.append("removed for day trading: " + "; ".join(f"{', '.join(v)} ({k})" for k, v in by.items()))
        if num in MODERN_NOTES:
            notes.append(MODERN_NOTES[num])
        out.append({"num": num, "name": name, "sub": sub, "members": members, "notes": notes})
    return out


def modern_symbols(kind=None):
    out = [s for sec in modern_layout() for s, k, _ in sec["members"] if k != "n/a" and (kind is None or k == kind)]
    assert len(out) == len(set(out)), "Modern universe has duplicates"
    assert not set(out) & set(MAG7), "Modern universe must exclude MAG 7"
    return out


def ratings_symbols(agent):
    """Analyst ratings only make sense for stocks (not ETFs)."""
    return modern_symbols("Stock") if agent == "modern" else symbols(agent)[0]


def symbols(agent):
    if agent == "mag7":
        return MAG7, MAG7_BENCHMARKS
    if agent == "aisectors":
        return ai_symbols(), AI_BENCHMARKS
    if agent == "modern":
        return modern_symbols(), MODERN_BENCHMARKS
    raise ValueError(f"unknown agent {agent!r}")
