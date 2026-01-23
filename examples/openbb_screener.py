"""
OpenBB Stock Screener Example

This example demonstrates using OpenBB to screen for stocks
by various criteria - something Yahoo Finance can't do!

Requirements:
    pip install openbb

For more info: https://openbb.co/
"""

from indexforge.data.connectors.openbb import OpenBBConnector

# Initialize OpenBB connector
connector = OpenBBConnector()

print("=" * 60)
print("OpenBB Stock Screener - Free Bloomberg Alternative")
print("=" * 60)

# Example 1: Search for Chinese tech companies
print("\n📍 Searching for 'alibaba'...")
results = connector.search_stocks("alibaba", limit=5)
for r in results:
    print(f"  - {r.get('symbol', 'N/A')}: {r.get('name', 'Unknown')}")

# Example 2: Get S&P 500 constituents
print("\n📊 Getting S&P 500 constituents...")
try:
    sp500 = connector.get_index_constituents("SP500")
    print(f"  Found {len(sp500)} stocks in S&P 500")
    print(f"  First 10: {sp500[:10]}")
except Exception as e:
    print(f"  (Index constituents not available: {e})")

# Example 3: Get constituent data for known tickers
print("\n📈 Fetching data for FAANG stocks...")
faang = ["META", "AAPL", "AMZN", "NFLX", "GOOGL"]
constituents = connector.get_constituent_data(faang)

print(f"\n{'Ticker':<8} {'Name':<25} {'Sector':<20} {'Market Cap':>15}")
print("-" * 75)
for c in sorted(constituents, key=lambda x: x.market_cap or 0, reverse=True):
    market_cap_str = f"${c.market_cap/1e9:.1f}B" if c.market_cap else "N/A"
    print(f"{c.ticker:<8} {c.name[:25]:<25} {c.sector[:20]:<20} {market_cap_str:>15}")

# Example 4: Try stock screening (if available)
print("\n🔍 Attempting stock screening...")
try:
    screened = connector.screen_stocks(
        sector="technology",  # Must be lowercase for OpenBB
        min_market_cap=100_000_000_000,  # $100B+
        limit=10,
    )
    if screened:
        print(f"  Found {len(screened)} large-cap tech stocks")
        for s in screened[:5]:
            print(f"  - {s.get('symbol', 'N/A')}: {s.get('name', 'Unknown')}")
    else:
        print("  (Screening returned no results - try different criteria)")
except Exception as e:
    print(f"  (Screening not available with current provider: {e})")

print("\n" + "=" * 60)
print(f"Data source: {connector.get_name()}")
print("=" * 60)
