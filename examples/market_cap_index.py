#!/usr/bin/env python3
"""
Market Cap Weighted Index Example

This example shows how to create a market cap weighted index
with weight caps and quarterly rebalancing.

Run with: python examples/market_cap_index.py
"""

from indexforge import (
    Currency,
    Factor,
    Index,
    RebalancingSchedule,
    Sector,  # New: enum for sectors
    SelectionCriteria,
    Universe,
    ValidationRules,
    WeightingMethod,
)


def main():
    """Create a market cap weighted index."""

    print("=" * 60)
    print("Creating Market Cap Weighted Index")
    print("=" * 60)
    print()

    # Step 1: Create the index
    index = Index.create(
        name="Tech Leaders Index",
        identifier="TECHLDRS",
        currency=Currency.USD,
        base_date="2024-01-01",
        base_value=1000.0,
        isin="DE000SL0XYZ1",
    )

    print(f"✅ Created index: {index.name}")

    # Step 2: Define the universe with criteria
    # Note: Using Sector enum provides IDE autocomplete!
    universe = (
        Universe.builder()
        .asset_class("EQUITIES")
        .sectors([Sector.TECHNOLOGY, Sector.COMMUNICATION_SERVICES])
        .tickers(
            [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "META",
                "NVDA",
                "TSLA",
                "CRM",
                "ADBE",
                "NFLX",
                "ORCL",
                "CSCO",
                "INTC",
                "AMD",
                "QCOM",
            ]
        )
        .min_market_cap(50_000_000_000)  # $50B minimum
        .build()
    )

    print(f"✅ Defined universe with {len(universe.tickers)} stocks")
    print(f"   Minimum market cap: ${universe.min_market_cap:,.0f}")

    # Step 3: Set selection criteria
    selection = (
        SelectionCriteria.builder()
        .ranking_by(Factor.MARKET_CAP)
        .select_top(10)
        .apply_buffer_rules(
            add_threshold=8,  # Must rank in top 8 to be added
            remove_threshold=15,  # Must fall below rank 15 to be removed
        )
        .build()
    )

    print(f"✅ Selection: Top {selection.select_count} by market cap")
    print(
        f"   Buffer: Add at rank {selection.buffer_rules.add_threshold}, "
        f"Remove below rank {selection.buffer_rules.remove_threshold}"
    )

    # Step 4: Set market cap weighting with caps
    weighting = (
        WeightingMethod.market_cap()
        .with_cap(max_weight=0.15)  # 15% max per stock
        .with_cap(max_weight_per_sector=0.50)  # 50% max per sector
        .build()
    )

    print("✅ Weighting: Market cap with 15% cap per constituent")

    # Step 5: Set quarterly rebalancing
    rebalancing = (
        RebalancingSchedule.builder()
        .frequency("quarterly")
        .on_months([3, 6, 9, 12])
        .on_day(15)
        .selection_date_offset(10)  # Selection data 10 business days before
        .announcement_date_offset(5)  # Announce 5 business days before
        .build()
    )

    print(f"✅ Rebalancing: {rebalancing.frequency.value}")

    # Step 6: Set validation rules
    validation = (
        ValidationRules.builder()
        .min_constituents(5)
        .max_constituents(15)
        .max_single_constituent_weight(0.20)
        .build()
    )

    print("✅ Validation rules configured")

    # Step 7: Configure the index
    (
        index.set_universe(universe)
        .set_selection_criteria(selection)
        .set_weighting_method(weighting)
        .set_rebalancing_schedule(rebalancing)
        .set_validation_rules(validation)
    )

    # Step 8: Validate configuration
    report = index.validate()
    if report.is_valid:
        print("✅ Index configuration is valid")
    else:
        print("⚠️  Configuration issues:")
        for error in report.errors:
            print(f"   {error.severity.value}: {error.message}")

    # Step 9: Print summary using direct property access (best practice!)
    print()
    print("=" * 60)
    print("INDEX CONFIGURATION SUMMARY")
    print("=" * 60)

    # Access properties directly - clean and type-safe
    print(
        f"""
Name:            {index.name}
Identifier:      {index.identifier}
ISIN:            {index.isin}
Currency:        {index.currency}
Base Date:       {index.base_date}
Base Value:      {index.base_value:,.2f}
Index Type:      {index.index_type}

Universe:
  Asset Class:   {index.universe.asset_class}
  Sectors:       {', '.join(index.universe.sectors)}
  Min Mkt Cap:   ${index.universe.min_market_cap:,.0f}
  Stocks:        {len(index.universe.tickers)}

Selection:
  Method:        Top {index.selection_criteria.select_count} by {index.selection_criteria.ranking_factor}
  Add Buffer:    Rank {index.selection_criteria.buffer_rules.add_threshold}
  Remove Buffer: Rank {index.selection_criteria.buffer_rules.remove_threshold}

Weighting:
  Scheme:        {index.weighting_method.scheme}
  Max Weight:    {index.weighting_method.caps.max_weight:.0%}

Rebalancing:
  Frequency:     {index.rebalancing_schedule.frequency}
  Day:           {index.rebalancing_schedule.day}th
  Months:        {index.rebalancing_schedule.months}
    """
    )

    # Step 10: Save configuration
    index.save("solgtech_config.json")
    print("✅ Configuration saved to 'solgtech_config.json'")

    print()
    print("=" * 60)
    print("INDEX READY FOR CALCULATION")
    print("=" * 60)
    print()
    print("To calculate the index value, uncomment the calculation code")
    print("in this script. Requires yfinance for market data.")

    # Uncomment to calculate (requires internet connection):
    # print("\nCalculating index...")
    # try:
    #     backtest = index.backtest(
    #         start_date="2024-01-01",
    #         end_date="2024-11-15",
    #         initial_value=1000.0
    #     )
    #     print(backtest)
    # except Exception as e:
    #     print(f"Error: {e}")


if __name__ == "__main__":
    main()
