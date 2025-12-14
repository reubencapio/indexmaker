#!/usr/bin/env python3
"""
ACME Indexmaker Global Large & Mid Cap Example (PDF 1)
==========================================================

Implements a demonstrator for the core guideline document
"Guideline – ACME Indexmaker Series (1).pdf"
covering the global developed universe.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from acme_indexmaker_common import (
    GENERAL_THRESHOLD,
    TOP_BUFFER,
    SampleSecurity,
    build_constituents,
    indexmaker_rebalancing_schedule,
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

CONFIG_PATH = Path("acme_indexmaker_global_large_mid.json")


def build_sample_constituents() -> list[Constituent]:
    """Create a representative developed-world sample."""

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
            "NESN",
            "Nestlé SA",
            "Switzerland",
            "Consumer Staples",
            330_000_000_000,
            0.90,
            4_200_000,
            Currency.CHF,
        ),
        SampleSecurity(
            "LVMH",
            "LVMH Moet Hennessy",
            "France",
            "Consumer Discretionary",
            470_000_000_000,
            0.89,
            2_600_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "ASML",
            "ASML Holding NV",
            "Netherlands",
            "Information Technology",
            360_000_000_000,
            0.87,
            3_200_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "SAP",
            "SAP SE",
            "Germany",
            "Information Technology",
            190_000_000_000,
            0.86,
            2_000_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "HSBA",
            "HSBC Holdings",
            "United Kingdom",
            "Financials",
            165_000_000_000,
            0.85,
            6_100_000,
            Currency.GBP,
        ),
        SampleSecurity(
            "SHEL",
            "Shell plc",
            "United Kingdom",
            "Energy",
            230_000_000_000,
            0.88,
            5_500_000,
            Currency.GBP,
        ),
        SampleSecurity(
            "TM",
            "Toyota Motor",
            "Japan",
            "Consumer Discretionary",
            310_000_000_000,
            0.80,
            7_200_000,
            Currency.JPY,
        ),
        SampleSecurity(
            "SONY",
            "Sony Group",
            "Japan",
            "Communication Services",
            110_000_000_000,
            0.80,
            3_500_000,
            Currency.JPY,
        ),
        SampleSecurity(
            "BHP",
            "BHP Group",
            "Australia",
            "Materials",
            150_000_000_000,
            0.78,
            4_000_000,
            Currency.AUD,
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
            "TCS",
            "Tata Consultancy Services",
            "India",
            "Information Technology",
            160_000_000_000,
            0.70,
            6_000_000,
            Currency.INR,
        ),
        SampleSecurity(
            "0700.HK",
            "Tencent Holdings",
            "Hong Kong",
            "Communication Services",
            360_000_000_000,
            0.65,
            10_000_000,
            Currency.HKD,
        ),
    ]

    return build_constituents(samples)


def configure_index(selected: list[Constituent]) -> Index:
    """Wire each IndexMaker component following the guideline."""

    tickers = [c.ticker for c in selected]
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .regions([Region.GLOBAL])
        .countries(
            [
                Country.UNITED_STATES,
                Country.CANADA,
                Country.UNITED_KINGDOM,
                Country.FRANCE,
                Country.GERMANY,
                Country.NETHERLANDS,
                Country.SWITZERLAND,
                Country.JAPAN,
                Country.AUSTRALIA,
                Country.HONG_KONG,
                Country.INDIA,
            ]
        )
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
    rebalancing = indexmaker_rebalancing_schedule()
    validation = (
        ValidationRules.builder()
        .min_constituents(int(select_count * 0.8))
        .max_constituents(int(select_count * 1.2))
        .max_single_constituent_weight(0.12)
        .max_single_country_weight(0.35)
        .max_single_sector_weight(0.30)
        .build()
    )

    return (
        Index.create(
            name="ACME Indexmaker Global Large & Mid Cap (Demo)",
            identifier="IMGLB85",
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
    print("ACME Indexmaker Global Large & Mid Cap (Guideline Demo)")
    print("=" * 80)
    print("Guideline source: PDF (1) – Global benchmark overview")

    constituents = build_sample_constituents()
    bucket = select_large_mid_bucket(constituents)
    selected = bucket.selected

    print(
        f"\nSelected {len(selected)} constituents covering >= {GENERAL_THRESHOLD:.0%} of free-float."
    )
    print_selection_audit(bucket.audit_rows)

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
    print(f"Universe:    {len(index.universe.tickers)} global large & mid caps")
    print(f"Weighting:   {index.weighting_method.scheme}")
    print("Rebalance:   Feb/May/Aug/Nov (first Wednesday per guideline)")
    print(f"Saved file:  {CONFIG_PATH.resolve()}")


if __name__ == "__main__":
    main()
