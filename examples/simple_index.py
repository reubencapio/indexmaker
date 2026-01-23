#!/usr/bin/env python3
"""
Simple Index Example

This example shows how to create a simple equal-weighted index
using free Yahoo Finance data.

Run with: python examples/simple_index.py
"""

from indexforge import (
    Currency,
    Index,
    Universe,
    WeightingMethod,
)


def main():
    """Create a simple equal-weighted index."""

    print("=" * 60)
    print("Creating Simple Equal-Weighted Index")
    print("=" * 60)
    print()

    # Step 1: Create the index
    index = Index.create(
        name="Simple Tech Index",
        identifier="SIMTECH",
        currency=Currency.USD,
        base_date="2024-01-01",
        base_value=1000.0,
    )

    print(f"✅ Created index: {index.name} ({index.identifier})")

    # Step 2: Define the universe (which stocks can be in the index)
    universe = Universe.from_tickers(
        [
            "AAPL",  # Apple
            "MSFT",  # Microsoft
            "GOOGL",  # Alphabet
            "AMZN",  # Amazon
            "META",  # Meta
        ]
    )

    print(f"✅ Defined universe with {len(universe.tickers)} stocks")

    # Step 3: Set equal weighting
    weighting = WeightingMethod.equal_weight()

    print("✅ Using equal-weight methodology")

    # Step 4: Configure the index
    index.set_universe(universe)
    index.set_weighting_method(weighting)

    # Step 5: Validate configuration
    report = index.validate()
    if report.is_valid:
        print("✅ Index configuration is valid")
    else:
        print("❌ Configuration issues found:")
        for error in report.errors:
            print(f"   - {error.message}")

    print()
    print("Index Configuration Summary:")
    print(f"  Name: {index.name}")
    print(f"  Identifier: {index.identifier}")
    print(f"  Currency: {index.currency}")
    print(f"  Base Date: {index.base_date}")
    print(f"  Base Value: {index.base_value}")
    print()

    # Note: To actually calculate the index, you need to fetch real data
    # Uncomment the lines below to calculate (requires internet connection)

    # print("Calculating index...")
    # try:
    #     constituents = index.get_constituents(date="2024-11-15")
    #     print(f"\n📊 Index Constituents:")
    #     for c in constituents:
    #         print(f"  {c.ticker}: {c.name} - Weight: {c.weight:.2%}")
    # except Exception as e:
    #     print(f"Error: {e}")

    print("=" * 60)
    print("Done! This was a simple example.")
    print("=" * 60)


if __name__ == "__main__":
    main()
