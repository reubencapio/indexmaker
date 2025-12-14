#!/usr/bin/env python3
"""
Indexmaker Emerging Markets Large & Mid Cap Example (PDF 4)
================================================================

Implements a demonstrator for "Guideline – Indexmaker
Series (4).pdf" covering the comprehensive Emerging
Markets block (Section 6).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

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
from indexmaker_common import (
    GENERAL_THRESHOLD,
    TOP_BUFFER,
    SampleSecurity,
    build_constituents,
    indexmaker_rebalancing_schedule,
    print_rebalance_calendar,
    print_selection_audit,
    select_large_mid_bucket,
)

CONFIG_PATH = Path("indexmaker_emerging_markets.json")


def build_sample_constituents() -> list[Constituent]:
    """Create a diverse Emerging Markets sample universe."""

    samples = [
        SampleSecurity(
            "BABA",
            "Alibaba Group",
            Country.CHINA,
            "Consumer Discretionary",
            190_000_000_000,
            0.65,
            15_000_000,
            Currency.CNY,
        ),
        SampleSecurity(
            "TCEHY",
            "Tencent Holdings",
            Country.CHINA,
            "Communication Services",
            360_000_000_000,
            0.65,
            10_000_000,
            Currency.CNY,
        ),
        SampleSecurity(
            "TSM",
            "Taiwan Semiconductor",
            Country.TAIWAN,
            "Information Technology",
            480_000_000_000,
            0.78,
            12_000_000,
            Currency.USD,
        ),
        SampleSecurity(
            "RELIANCE",
            "Reliance Industries",
            Country.INDIA,
            "Energy",
            230_000_000_000,
            0.70,
            9_000_000,
            Currency.INR,
        ),
        SampleSecurity(
            "TCS",
            "Tata Consultancy Services",
            Country.INDIA,
            "Information Technology",
            160_000_000_000,
            0.70,
            6_000_000,
            Currency.INR,
        ),
        SampleSecurity(
            "ITUB",
            "Itaú Unibanco",
            Country.BRAZIL,
            "Financials",
            60_000_000_000,
            0.65,
            5_000_000,
            Currency.BRL,
        ),
        SampleSecurity(
            "VALE",
            "Vale SA",
            Country.BRAZIL,
            "Materials",
            70_000_000_000,
            0.66,
            6_200_000,
            Currency.BRL,
        ),
        SampleSecurity(
            "PBR",
            "Petrobras",
            Country.BRAZIL,
            "Energy",
            80_000_000_000,
            0.60,
            5_500_000,
            Currency.BRL,
        ),
        SampleSecurity(
            "MTN",
            "MTN Group",
            Country.SOUTH_AFRICA,
            "Communication Services",
            25_000_000_000,
            0.55,
            1_600_000,
            None,
        ),
        SampleSecurity(
            "NPSNY",
            "Naspers Ltd.",
            Country.SOUTH_AFRICA,
            "Communication Services",
            35_000_000_000,
            0.60,
            1_900_000,
            None,
        ),
        SampleSecurity(
            "SABIC",
            "Saudi Basic Industries",
            Country.SAUDI_ARABIA,
            "Materials",
            90_000_000_000,
            0.62,
            2_400_000,
            None,
        ),
        SampleSecurity(
            "QNBK",
            "Qatar National Bank",
            Country.QATAR,
            "Financials",
            50_000_000_000,
            0.60,
            1_400_000,
            None,
        ),
        SampleSecurity(
            "005930.KS",
            "Samsung Electronics",
            Country.SOUTH_KOREA,
            "Information Technology",
            360_000_000_000,
            0.74,
            8_000_000,
            Currency.KRW,
        ),
        SampleSecurity(
            "MELI",
            "MercadoLibre",
            Country.ARGENTINA,
            "Consumer Discretionary",
            80_000_000_000,
            0.65,
            3_800_000,
            Currency.USD,
        ),
    ]

    return build_constituents(samples)


def configure_index(selected: list[Constituent]) -> Index:
    """Wire components for the Emerging Markets block."""

    tickers = [c.ticker for c in selected]
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .regions([Region.EMERGING_MARKETS])
        .countries(
            [
                Country.BRAZIL,
                Country.CHILE,
                Country.CHINA,
                Country.COLOMBIA,
                Country.CZECH_REPUBLIC,
                Country.EGYPT,
                Country.GREECE,
                Country.HUNGARY,
                Country.INDIA,
                Country.INDONESIA,
                Country.KUWAIT,
                Country.MALAYSIA,
                Country.MEXICO,
                Country.PHILIPPINES,
                Country.QATAR,
                Country.SAUDI_ARABIA,
                Country.SOUTH_AFRICA,
                Country.SOUTH_KOREA,
                Country.TAIWAN,
                Country.THAILAND,
                Country.TURKEY,
                Country.UNITED_ARAB_EMIRATES,
            ]
        )
        .tickers(tickers)
        .min_market_cap(10_000_000_000, currency=Currency.USD)
        .min_average_daily_volume(1_500_000)
        .min_free_float(0.4)
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
        .max_single_constituent_weight(0.10)
        .max_single_country_weight(0.25)
        .max_single_sector_weight(0.30)
        .build()
    )

    return (
        Index.create(
            name="Indexmaker Emerging Markets Large & Mid Cap (Demo)",
            identifier="IMEMR85",
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
    """Run the example."""

    print("=" * 80)
    print("Indexmaker Emerging Markets Large & Mid Cap (Guideline Demo)")
    print("=" * 80)
    print("Guideline source: PDF (4) – Emerging Markets block")

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
    print(f"Universe:    {len(index.universe.tickers)} Emerging Markets large & mid caps")
    print(f"Weighting:   {index.weighting_method.scheme}")
    print("Rebalance:   Feb/May/Aug/Nov (first Wednesday per guideline)")
    print(f"Saved file:  {CONFIG_PATH.resolve()}")


if __name__ == "__main__":
    main()
