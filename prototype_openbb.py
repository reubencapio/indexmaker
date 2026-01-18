from openbb import obb

print("Testing 'growth_tech' discovery...")
try:
    res = obb.equity.discovery.growth_tech(provider="yfinance")
    df = res.to_df()
    print(f"Found {len(df)} tickers")
    print(df.head())
except Exception as e:
    print(f"Error growth_tech: {e}")

print("\nTesting 'active' discovery...")
try:
    res = obb.equity.discovery.active(provider="yfinance")
    df = res.to_df()
    print(f"Found {len(df)} tickers")
    print(df.head())
except Exception as e:
    print(f"Error active: {e}")
