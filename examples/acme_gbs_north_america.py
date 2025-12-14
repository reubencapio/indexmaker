#!/usr/bin/env python3
"""
ACME GBS North America Large & Mid Cap Example
===================================================

This example translates the ACME GBS guideline (v3.04 – 01 July 2024) into
a concrete IndexMaker configuration. It follows the key design points in
Section 2 of the document:

* Country alignment and listing hierarchy (Section 2.1.1 & 2.1.2)
* Size-bucket construction based on cumulative free-float market cap (Section 2.1.3)
* Regional roll-up (Section 2.1.4)
* Quarterly rebalancing on the first Wednesday in Feb/May/Aug/Nov (Section 2.2)
* Free-float market-cap weighting (Section 2.4)

Run with: python examples/acme_gbs_north_america.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from acme_gbs_common import (
    GENERAL_THRESHOLD,
    TOP_BUFFER,
    SampleSecurity,
    build_constituents,
    gbs_rebalancing_schedule,
    print_rebalance_calendar,
    print_selection_audit,
    select_large_mid_bucket,
)
from indexmaker import (
    AssetClass,
    Constituent,
    Country,
    Currency,
    Factor,
    Index,
    Region,
    SelectionCriteria,
    Universe,
    ValidationRules,
    WeightingMethod,
)

GBS_VERSION = "3.04"
SIZE_BUCKET = "Large & Mid Cap"
CONFIG_PATH = Path("acme_gbs_na_large_mid.json")


def build_sample_constituents() -> list[Constituent]:
    """
    Craft a small proxy universe for demonstration purposes.

    Real production flows would pull these fields from ACME's upstream data
    sources. All market caps are in USD for readability.
    """

    samples = [
        SampleSecurity(
            "AAPL",
            "Apple Inc.",
            "United States",
            "Information Technology",
            3_350_000_000_000,
            0.99,
            95_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "MSFT",
            "Microsoft Corp.",
            "United States",
            "Information Technology",
            3_200_000_000_000,
            0.99,
            32_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "NVDA",
            "NVIDIA Corp.",
            "United States",
            "Information Technology",
            2_900_000_000_000,
            0.98,
            60_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "AMZN",
            "Amazon.com Inc.",
            "United States",
            "Consumer Discretionary",
            1_900_000_000_000,
            0.90,
            45_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "META",
            "Meta Platforms Inc.",
            "United States",
            "Communication Services",
            1_350_000_000_000,
            0.96,
            25_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "TSLA",
            "Tesla Inc.",
            "United States",
            "Consumer Discretionary",
            780_000_000_000,
            0.88,
            38_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "JPM",
            "JPMorgan Chase & Co.",
            "United States",
            "Financials",
            570_000_000_000,
            0.92,
            13_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "JNJ",
            "Johnson & Johnson",
            "United States",
            "Health Care",
            400_000_000_000,
            0.88,
            8_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "V",
            "Visa Inc.",
            "United States",
            "Financials",
            520_000_000_000,
            0.98,
            6_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "MA",
            "Mastercard Inc.",
            "United States",
            "Financials",
            430_000_000_000,
            0.97,
            5_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "RY",
            "Royal Bank of Canada",
            "Canada",
            "Financials",
            150_000_000_000,
            0.80,
            6_500_000,
            Currency.CAD,
        ),
        SampleSecurity(
            "TD",
            "Toronto-Dominion Bank",
            "Canada",
            "Financials",
            120_000_000_000,
            0.80,
            6_000_000,
            Currency.CAD,
        ),
        SampleSecurity(
            "ENB",
            "Enbridge Inc.",
            "Canada",
            "Energy",
            110_000_000_000,
            0.75,
            4_500_000,
            Currency.CAD,
        ),
        SampleSecurity(
            "SHOP",
            "Shopify Inc.",
            "Canada",
            "Information Technology",
            75_000_000_000,
            0.66,
            8_500_000,
            Currency.CAD,
        ),
        SampleSecurity(
            "CNQ",
            "Canadian Natural Resources",
            "Canada",
            "Energy",
            95_000_000_000,
            0.70,
            3_700_000,
            Currency.CAD,
        ),
        SampleSecurity(
            "BNS",
            "Bank of Nova Scotia",
            "Canada",
            "Financials",
            90_000_000_000,
            0.78,
            4_000_000,
            Currency.CAD,
        ),
    ]

    return build_constituents(samples)


def configure_index(selected: list[Constituent]) -> Index:
    """Wire every IndexMaker component so the configuration can be saved."""

    tickers = [c.ticker for c in selected]
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .regions([Region.NORTH_AMERICA])
        .countries([Country.UNITED_STATES, Country.CANADA])
        .tickers(tickers)
        .min_market_cap(50_000_000_000, currency=Currency.USD)
        .min_average_daily_volume(5_000_000)
        .min_free_float(0.5)
        .build()
    )

    select_count = len(tickers)
    add_threshold = max(1, int(select_count * TOP_BUFFER))
    remove_threshold = max(select_count, int(select_count * 1.1))

    selection = (
        SelectionCriteria.builder()
        .ranking_by(Factor.FREE_FLOAT_MARKET_CAP)
        .select_top(select_count)
        .apply_buffer_rules(add_threshold=add_threshold, remove_threshold=remove_threshold)
        .build()
    )

    weighting = WeightingMethod.free_float_market_cap().build()
    rebalancing = gbs_rebalancing_schedule()
    validation = (
        ValidationRules.builder()
        .min_constituents(int(select_count * 0.8))
        .max_constituents(int(select_count * 1.2))
        .max_single_constituent_weight(0.12)
        .max_single_country_weight(0.65)
        .max_single_sector_weight(0.30)
        .build()
    )

    return (
        Index.create(
            name="ACME GBS North America Large & Mid Cap (Demo)",
            identifier="GBSNA85",
            currency=Currency.USD,
            base_date="2024-07-01",
            base_value=1_000.0,
        )
        .set_universe(universe)
        .set_selection_criteria(selection)
        .set_weighting_method(weighting)
        .set_rebalancing_schedule(rebalancing)
        .set_validation_rules(validation)
    )


def main() -> None:
    """Drive the full example."""

    print("=" * 80)
    print("ACME GBS North America Large & Mid Cap (Guideline Demo)")
    print("=" * 80)
    print(f"Guideline version: {GBS_VERSION}  |  Size bucket: {SIZE_BUCKET}")

    constituents = build_sample_constituents()
    bucket = select_large_mid_bucket(constituents)
    selected = bucket.selected

    print(
        f"\nSelected {len(selected)} constituents covering >= {GENERAL_THRESHOLD:.0%} of free-float."
    )
    print_selection_audit(bucket.audit_rows)

    # Configure the index
    index = configure_index(selected)
    report = index.validate()
    if not report.is_valid:
        print("\n⚠️  Validation issues detected:")
        for issue in report.errors:
            print(f"   - {issue.severity.value}: {issue.message}")
    else:
        print("\n✅ Index configuration passes validation rules.")

    index.save(CONFIG_PATH.as_posix())
    print(f"✅ Configuration saved to {CONFIG_PATH}")

    print("\nRebalancing cadence (first Wednesday rule):")
    print_rebalance_calendar(start_year=date.today().year)

    print("\nSummary")
    print("-" * 80)
    print(f"Name:        {index.name}")
    print(f"Identifier:  {index.identifier}")
    print(f"Universe:    {len(index.universe.tickers)} North American large & mid caps")
    print(f"Weighting:   {index.weighting_method.scheme}")
    print("Rebalance:   Feb/May/Aug/Nov (first Wednesday per guideline)")
    print(f"Saved file:  {CONFIG_PATH.resolve()}")


if __name__ == "__main__":
    main()
