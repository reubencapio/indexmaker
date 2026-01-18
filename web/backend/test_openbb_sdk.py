
from openbb import obb


def test_openbb_features():
    print("Testing OpenBB SDK...")

    # Test 1: Search (for context)
    try:
        print("\n--- Testing Search (AAPL) ---")
        # Note: 'provider' argument might be needed depending on default settings
        res = obb.equity.search("AAPL")
        print(f"Search result type: {type(res)}")
        # OpenBB v4 returns an OBBject, usually accessible via .results
        if hasattr(res, "results"):
            print(f"First result: {res.results[0] if res.results else 'No results'}")
        else:
            print(res)
    except Exception as e:
        print(f"Search failed: {e}")

    # Test 2: ESG Data
    # Common providers for ESG might be 'fmp' or others if configured.
    # If no provider key is set, this might fail or return empty.
    # We'll try to find where ESG data lives in v4. Maybe `equity.fundamental.esg`?
    try:
        print("\n--- Testing ESG (AAPL) ---")
        # Speculative path for v4 - checking docs via trial
        # Note: If this fails, I'll know to look for alternatives
        try:
            res = obb.equity.fundamental.management_quality(symbol="AAPL")
            print(f"Mgmt Quality found: {res.results}")
        except Exception:
            print("Standard ESG endpoint not found or failed.")

    except Exception as e:
        print(f"ESG failed: {e}")

    # Test 3: Dividends
    try:
        print("\n--- Testing Dividends (AAPL) ---")
        res = obb.equity.fundamental.dividends(symbol="AAPL")
        if hasattr(res, "results"):
            print(f"Dividends found: {len(res.results)} records")
            print(res.results[-1] if res.results else "Empty")
    except Exception as e:
        print(f"Dividends failed: {e}")


if __name__ == "__main__":
    test_openbb_features()
