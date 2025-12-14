#!/usr/bin/env python3
"""
ACME GBS Developed Pacific Large & Mid Cap Example (PDF 3)
===============================================================

Implements a demonstrator for "Guideline – ACME Global
Benchmark Series (3).pdf" focusing on the Developed Markets
Pacific block (Australia, Hong Kong, Japan, New Zealand, Singapore).
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

CONFIG_PATH = Path("acme_gbs_developed_pacific.json")


def build_sample_constituents() -> list[Constituent]:
    """Create a Developed Markets Pacific sample universe."""

    samples = [
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
            "NTDOY",
            "Nintendo Co.",
            "Japan",
            "Communication Services",
            60_000_000_000,
            0.78,
            2_600_000,
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
            "CSL",
            "CSL Ltd.",
            "Australia",
            "Health Care",
            95_000_000_000,
            0.75,
            1_800_000,
            Currency.AUD,
        ),
        SampleSecurity(
            "TCL",
            "Transurban Group",
            "Australia",
            "Industrials",
            45_000_000_000,
            0.72,
            1_200_000,
            Currency.AUD,
        ),
        SampleSecurity(
            "388.HK",
            "Hong Kong Exchanges",
            "Hong Kong",
            "Financials",
            55_000_000_000,
            0.70,
            2_200_000,
            Currency.HKD,
        ),
        SampleSecurity(
            "0005.HK",
            "HSBC Holdings (HK listing)",
            "Hong Kong",
            "Financials",
            165_000_000_000,
            0.85,
            5_800_000,
            Currency.HKD,
        ),
        SampleSecurity(
            "AIA",
            "AIA Group",
            "Hong Kong",
            "Financials",
            90_000_000_000,
            0.68,
            3_300_000,
            Currency.HKD,
        ),
        SampleSecurity(
            "D05",
            "DBS Group",
            "Singapore",
            "Financials",
            65_000_000_000,
            0.70,
            2_500_000,
            Currency.SGD,
        ),
        SampleSecurity(
            "C52",
            "Oversea-Chinese Banking",
            "Singapore",
            "Financials",
            45_000_000_000,
            0.68,
            1_900_000,
            Currency.SGD,
        ),
        SampleSecurity(
            "AIR.NZ",
            "Air New Zealand",
            "New Zealand",
            "Industrials",
            10_000_000_000,
            0.60,
            800_000,
            Currency.NZD,
        ),
    ]

    return build_constituents(samples)


def configure_index(selected: list[Constituent]) -> Index:
    """Wire components for the Developed Pacific block."""

    tickers = [c.ticker for c in selected]
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .regions([Region.ASIA_PACIFIC])
        .countries(
            [
                Country.AUSTRALIA,
                Country.HONG_KONG,
                Country.JAPAN,
                Country.NEW_ZEALAND,
                Country.SINGAPORE,
            ]
        )
        .tickers(tickers)
        .min_market_cap(15_000_000_000, currency=Currency.USD)
        .min_average_daily_volume(1_500_000)
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
        .max_single_country_weight(0.40)
        .max_single_sector_weight(0.30)
        .build()
    )

    return (
        Index.create(
            name="ACME GBS Developed Pacific Large & Mid Cap (Demo)",
            identifier="GBSPAC85",
            currency=Currency.JPY,
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
    """Run the example."""

    print("=" * 80)
    print("ACME GBS Developed Pacific Large & Mid Cap (Guideline Demo)")
    print("=" * 80)
    print("Guideline source: PDF (3) – Developed Markets Pacific block")

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
    print(f"Universe:    {len(index.universe.tickers)} Developed Pacific large & mid caps")
    print(f"Weighting:   {index.weighting_method.scheme}")
    print("Rebalance:   Feb/May/Aug/Nov (first Wednesday per guideline)")
    print(f"Saved file:  {CONFIG_PATH.resolve()}")


if __name__ == "__main__":
    main()
