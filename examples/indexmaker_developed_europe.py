#!/usr/bin/env python3
"""
Indexmaker Developed Europe Large & Mid Cap Example (PDF 2)
================================================================

Implements a demonstrator for "Guideline – Indexmaker
Series (2).pdf" focusing on the Developed Markets Europe block listed
in Section 6 of the document.
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

CONFIG_PATH = Path("indexmaker_developed_europe.json")


def build_sample_constituents() -> list[Constituent]:
    """Create a Developed Markets Europe sample universe."""

    samples = [
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
            "SIE",
            "Siemens AG",
            "Germany",
            "Industrials",
            140_000_000_000,
            0.85,
            1_800_000,
            Currency.EUR,
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
            "MC.PA",
            "Hermès International",
            "France",
            "Consumer Discretionary",
            250_000_000_000,
            0.85,
            1_400_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "NOVN",
            "Novartis AG",
            "Switzerland",
            "Health Care",
            210_000_000_000,
            0.84,
            2_100_000,
            Currency.CHF,
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
            "ULVR",
            "Unilever plc",
            "United Kingdom",
            "Consumer Staples",
            120_000_000_000,
            0.82,
            2_500_000,
            Currency.GBP,
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
            "SAN",
            "Banco Santander",
            "Spain",
            "Financials",
            70_000_000_000,
            0.80,
            4_500_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "ENEL",
            "Enel SpA",
            "Italy",
            "Utilities",
            65_000_000_000,
            0.78,
            3_100_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "ORSTED",
            "Ørsted A/S",
            "Denmark",
            "Utilities",
            35_000_000_000,
            0.70,
            1_700_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "VOLV-B",
            "Volvo AB",
            "Sweden",
            "Industrials",
            55_000_000_000,
            0.78,
            1_300_000,
            Currency.EUR,
        ),
        SampleSecurity(
            "EQNR",
            "Equinor ASA",
            "Norway",
            "Energy",
            90_000_000_000,
            0.82,
            2_600_000,
            Currency.EUR,
        ),
    ]

    return build_constituents(samples)


def configure_index(selected: list[Constituent]) -> Index:
    """Wire each component per guideline."""

    tickers = [c.ticker for c in selected]
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .regions([Region.EUROPE])
        .countries(
            [
                Country.AUSTRIA,
                Country.BELGIUM,
                Country.DENMARK,
                Country.FINLAND,
                Country.FRANCE,
                Country.GERMANY,
                Country.IRELAND,
                Country.ITALY,
                Country.NETHERLANDS,
                Country.NORWAY,
                Country.POLAND,
                Country.PORTUGAL,
                Country.SPAIN,
                Country.SWEDEN,
                Country.SWITZERLAND,
                Country.UNITED_KINGDOM,
            ]
        )
        .tickers(tickers)
        .min_market_cap(30_000_000_000, currency=Currency.EUR)
        .min_average_daily_volume(2_000_000)
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
        .max_single_country_weight(0.30)
        .max_single_sector_weight(0.30)
        .build()
    )

    return (
        Index.create(
            name="Indexmaker Developed Europe Large & Mid Cap (Demo)",
            identifier="IMEUR85",
            currency=Currency.EUR,
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
    print("Indexmaker Developed Europe Large & Mid Cap (Guideline Demo)")
    print("=" * 80)
    print("Guideline source: PDF (2) – Developed Markets Europe block")

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
    print(f"Universe:    {len(index.universe.tickers)} Developed Europe large & mid caps")
    print(f"Weighting:   {index.weighting_method.scheme}")
    print("Rebalance:   Feb/May/Aug/Nov (first Wednesday per guideline)")
    print(f"Saved file:  {CONFIG_PATH.resolve()}")


if __name__ == "__main__":
    main()
