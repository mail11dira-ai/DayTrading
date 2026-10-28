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


# AI Sectors 100 (2026-10-20): ONE agent replacing AI Sectors + Modern AI Sectors. The best 100 unique
# stocks (no ETFs, no MAG 7) out of both agents' stocks plus 41 extra high-volume candidates (120 in total),
# ranked on 20-day Robinhood data: hard screen ($200M+/day, price >= $5, ATR >= 2.5%), then the average of
# the percentile ranks of dollar volume and ATR %. Same layout as MODERN (no ETF column).
AI100_BENCHMARKS = ["SPY", "QQQ"]
AI100 = [
    ("01", "Semiconductors & Memory", "GPUs | Analog | Memory | Foundry | Equipment",
     [], ["TXN", "ALAB", "MCHP", "MRVL", "AVGO", "AMD", "INTC", "QCOM", "ON", "SNDK", "TSM", "MU", "KLAC", "LRCX", "AMAT", "ASML", "TER"]),
    ("02", "AI Infrastructure / Networking / Optical", "Servers | Networking | Optical | Connectivity",
     [], ["SMCI", "HPE", "DELL", "ANET", "LITE", "COHR", "CRDO", "AAOI"]),
    ("03", "Neo-Cloud / AI Hosting", "AI hosting | Data centres | Bitcoin-miner hosting",
     [], ["NBIS", "IREN", "CIFR", "WULF", "CRWV"]),
    ("04", "Software & AI Apps", "Data | Apps | Enterprise | EDA",
     [], ["DDOG", "INTU", "APP", "IBM", "SNPS"]),
    ("05", "Cybersecurity", "Platforms | Endpoint | Network security",
     [], ["PANW", "CRWD", "FTNT"]),
    ("06", "Power / Energy / Nuclear", "Turbines | Utilities | Nuclear | Solar | Grid",
     [], ["GEV", "VST", "OKLO", "ETN", "FSLR", "SO", "NEE"]),
    ("07", "Metals & Miners", "Gold | Copper | Rare earths | Coal",
     [], ["MP", "CDE", "HL", "NEM"]),
    ("08", "Materials & Real Estate", "Industrial gases | REITs",
     [], ["LIN", "AMT"]),
    ("09", "Quantum", "Quantum computing",
     [], ["IONQ", "RGTI", "QBTS"]),
    ("10", "Industrials & Defense", "Machinery | Aerospace | Rail | Space",
     [], ["UNP", "GE", "HON", "CAT", "DE", "RKLB"]),
    ("11", "Airlines, Travel & Cruise", "Airlines | Cruise | Lodging",
     [], ["DAL", "UAL", "AAL", "RCL", "CCL", "ABNB"]),
    ("12", "Consumer & Internet", "Retail | Restaurants | Autos | Streaming | Gaming",
     [], ["SBUX", "NKE", "LOW", "HD", "ORLY", "RIVN", "CVNA", "DIS", "BABA", "DKNG", "LEN"]),
    ("13", "Consumer Staples", "Big-box retail | Household",
     [], ["WMT", "PG"]),
    ("14", "Healthcare", "Pharma | Biotech | Managed care | Tools | Devices",
     [], ["MRNA", "VRTX", "JNJ", "ABBV", "LLY", "UNH", "TMO", "ISRG"]),
    ("15", "Banks, Payments & Insurance", "Banks | Brokers | Payments | Insurance",
     [], ["GS", "WFC", "BLK", "V", "MA", "AFRM", "SOFI", "PGR"]),
    ("16", "Crypto & Bitcoin Miners", "Bitcoin treasury | Exchange | Stablecoin | Miners",
     [], ["MSTR", "COIN", "CRCL", "RIOT", "CLSK", "MARA"]),
]
# Super 10 (formerly Super 100; 2026-10-27): the user's list of 100 large / liquid US-listed leaders (MSFT was listed twice; SPCX added as #100), grouped
# by sector. Unlike the AI universes it INCLUDES the MAG 7 - this agent replaces the MAG 7 agent.
SUPER100_BENCHMARKS = ["SPY", "QQQ"]
SUPER100 = [
    ("01", "Mega-cap Tech", "Platforms | Devices | Cloud | Ads", [], ["GOOGL", "AAPL", "MSFT", "META", "AMZN", "NVDA"]),
    ("02", "Semiconductors", "AI accelerators | CPUs", [], ["AVGO", "AMD"]),
    ("03", "AI Data Center Infrastructure", "Power & cooling for AI data centres", [], ["VRT"]),
    ("04", "Cybersecurity", "Endpoint | Cloud security", [], ["CRWD"]),
    ("05", "Autos", "EVs | Energy storage", [], ["TSLA"]),
    ("06", "Space / Aerospace", "Launch | Satellites", [], ["SPCX"]),
]
INCLUDES_MAG7 = {"super100"}  # universes that list the MAG 7 themselves instead of deferring to the MAG 7 agent
USER_LISTS = {"super100", "ai100"}  # the user's own list: kept as given (no day-trading screen, no MODERN sector notes)
SECTOR_MAPS = {}  # filled below: agent -> sector list


def modern_layout(agent="modern"):
    """Sectors after de-duplication: list of dicts
    {num, name, sub, members: [(sym, kind, desc)], notes: [str]}; kind is 'ETF', 'Stock' or 'n/a'."""
    seen, out = {}, []
    removed = {} if agent in USER_LISTS else DAYTRADE_REMOVED
    for num, name, sub, etfs, leaders in SECTOR_MAPS[agent]:
        members, notes, dup = [], [], []
        cut = list(dict.fromkeys(x for x in [e for e, _ in etfs] + leaders if x in removed and x not in seen))
        for sym, desc in etfs:
            if sym in removed:
                seen.setdefault(sym, num)
                continue
            if sym in seen:
                dup.append(f"{sym} (in {seen[sym]})")
                continue
            seen[sym] = num
            members.append((sym, "n/a" if sym in NOT_ON_ROBINHOOD else "ETF", desc))
        mag = []
        for sym in leaders:
            if sym in removed:
                seen.setdefault(sym, num)
                continue
            if sym in MAG7 and agent not in INCLUDES_MAG7:
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
                by.setdefault(removed[x], []).append(x)
            notes.append("removed for day trading: " + "; ".join(f"{', '.join(v)} ({k})" for k, v in by.items()))
        if num in MODERN_NOTES and agent not in USER_LISTS:
            notes.append(MODERN_NOTES[num])
        out.append({"num": num, "name": name, "sub": sub, "members": members, "notes": notes})
    return out


SECTOR_MAPS.update(modern=MODERN, ai100=AI100, super100=SUPER100)


def modern_symbols(kind=None, agent="modern"):
    out = [s for sec in modern_layout(agent) for s, k, _ in sec["members"]
           if k != "n/a" and (kind is None or k == kind)]
    assert len(out) == len(set(out)), "Modern universe has duplicates"
    assert agent in INCLUDES_MAG7 or not set(out) & set(MAG7), "Modern universe must exclude MAG 7"
    return out


def ratings_symbols(agent):
    """Analyst ratings only make sense for stocks (not ETFs)."""
    return modern_symbols("Stock", agent) if agent in SECTOR_MAPS else symbols(agent)[0]


def symbols(agent):
    if agent == "mag7":
        return MAG7, MAG7_BENCHMARKS
    if agent == "aisectors":
        return ai_symbols(), AI_BENCHMARKS
    if agent == "modern":
        return modern_symbols(), MODERN_BENCHMARKS
    if agent == "ai100":
        return modern_symbols(agent="ai100"), AI100_BENCHMARKS
    if agent == "super100":
        return modern_symbols(agent="super100"), SUPER100_BENCHMARKS
    raise ValueError(f"unknown agent {agent!r}")
