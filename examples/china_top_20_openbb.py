"""
China Top 20 Technology Index - Using OpenBB Stock Screener

This example demonstrates DYNAMIC stock screening with OpenBB.
Unlike Yahoo Finance, OpenBB can find stocks by criteria!

OpenBB vs Yahoo Finance:
    - Yahoo: Must provide ticker symbols upfront (no screening)
    - OpenBB: Can screen by country, sector, market cap, etc.

Requirements:
    pip install openbb
"""

from indexmaker import Currency, Index, RebalancingSchedule, Universe, WeightingMethod
from indexmaker.data.connectors.openbb import OpenBBConnector

# Initialize OpenBB connector
connector = OpenBBConnector()

print("=" * 80)
print("OpenBB Stock Screener - Finding Chinese Tech Stocks Dynamically")
print("=" * 80)

# DYNAMIC SCREENING: Find Chinese tech stocks
# This is what Yahoo Finance CANNOT do!
print("\n🔍 Screening for technology stocks...")

try:
    # Try to screen for tech stocks
    # Note: OpenBB screening availability depends on the data provider
    screened_stocks = connector.screen_stocks(
        sector="technology", min_market_cap=1_000_000_000, limit=50  # $1B minimum
    )

    if screened_stocks:
        print(f"✅ Found {len(screened_stocks)} technology stocks via screening")
        tickers = [s.get("symbol", s.get("ticker", "")) for s in screened_stocks[:20]]
        tickers = [t for t in tickers if t]  # Filter out empty
    else:
        print("⚠️  Screening returned no results, using search fallback...")
        raise ValueError("No screening results")

except Exception as e:
    print(f"⚠️  Stock screening not available: {e}")
    print("\n📍 Falling back to searching for known Chinese tech companies...")

    # Fallback: Search for known Chinese tech companies
    search_terms = ["alibaba", "baidu", "jd.com", "nio", "xpeng", "bilibili", "netease"]
    tickers = []

    for term in search_terms:
        results = connector.search_stocks(term, limit=3)
        for r in results:
            ticker = r.get("symbol", r.get("ticker", ""))
            if ticker and ticker not in tickers:
                tickers.append(ticker)
                print(f"  Found: {ticker} - {r.get('name', 'Unknown')}")

        if len(tickers) >= 20:
            break

    # If still not enough, add known ADRs
    known_adrs = ["BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "NTES", "BILI", "TME"]
    for adr in known_adrs:
        if adr not in tickers:
            tickers.append(adr)
        if len(tickers) >= 20:
            break

print(f"\n📊 Selected {len(tickers)} stocks for index")

# Create the index
index = Index.create(
    name="China Technology Top 20 (OpenBB Screened)",
    identifier="CNTECH20OB",
    currency=Currency.USD,
    base_date="2025-12-15",
    base_value=1000,
)

# Define universe from screened tickers
universe = Universe.from_tickers(
    tickers=tickers[:20],
    currency=Currency.USD,
)

# Set equal weighting
weighting = WeightingMethod.equal_weight()

# Rebalancing schedule
rebalancing = RebalancingSchedule.quarterly()

# Configure the index
(index.set_universe(universe).set_weighting_method(weighting).set_rebalancing_schedule(rebalancing))

# Fetch full constituent data
print("\n📈 Fetching constituent data...")
constituents = connector.get_constituent_data(tickers[:20])

# Calculate equal weights
equal_weight = 1.0 / len(constituents) if constituents else 0

print(f"\n{'Ticker':<10} {'Name':<35} {'Sector':<20} {'Market Cap':>15} {'Weight':>10}")
print("-" * 100)

for c in sorted(constituents, key=lambda x: x.market_cap or 0, reverse=True):
    market_cap_str = f"${c.market_cap/1e9:.1f}B" if c.market_cap else "N/A"
    name = (c.name or c.ticker)[:35]
    sector = (c.sector or "Unknown")[:20]
    print(f"{c.ticker:<10} {name:<35} {sector:<20} {market_cap_str:>15} {equal_weight:>10.2%}")

print(f"\n{'=' * 80}")
print(f"Total constituents: {len(constituents)}")
print(f"Data source: {connector.get_name()}")
print(f"{'=' * 80}")

print(
    """
KEY DIFFERENCE:
  - Yahoo Finance: Requires you to KNOW the tickers upfront
  - OpenBB: Can FIND stocks by country, sector, market cap (when screening is available)

OpenBB screening depends on the data provider. The free providers have limited
screening capabilities. For full screening, consider providers like:
  - Financial Modeling Prep (FMP) - Has stock screener API
  - Polygon.io - Comprehensive data
"""
)
