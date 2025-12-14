#!/usr/bin/env python3
"""
ACME FAANG Index Example
============================

This script demonstrates how to configure the ACME FAANG Index as
described in “Guideline – ACME FAANG Series (Version 1.1 – 07-Jan-2021)”.

Features implemented from the guideline:
* Static FAANG basket: Alphabet, Amazon, Apple, Facebook (Meta) and Netflix.
* Share-class handling for Alphabet per Section 2.1.2.
* Free-float market-cap weighting for the primary index.
* Optional equal-weight replica mirroring the FAANG Equal Weight Index.
* Quarterly rebalancing.

Run with: python examples/acme_faang_index.py
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from acme_indexmaker_common import SampleSecurity, build_constituents, print_selection_audit
from indexmaker import (
    AssetClass,
    Constituent,
    Country,
    Currency,
    Factor,
    Index,
    RebalancingSchedule,
    Region,
    SelectionCriteria,
    Universe,
    ValidationRules,
    WeightingMethod,
)

CONFIG_CAP_PATH = Path("acme_faang_cap_weighted.json")
CONFIG_EQUAL_PATH = Path("acme_faang_equal_weight.json")


@dataclass(slots=True)
class CompanyShareClasses:
    """Helper for grouping share-class level sample data."""

    company: str
    classes: list[SampleSecurity]


def faang_share_class_samples() -> list[CompanyShareClasses]:
    """Build illustrative share-class data for the FAANG companies."""

    return [
        CompanyShareClasses(
            company="Alphabet",
            classes=[
                SampleSecurity(
                    ticker="GOOGL",
                    name="Alphabet Inc. Class A",
                    country="United States",
                    sector="Communication Services",
                    market_cap=1_900_000_000_000,
                    free_float=0.88,
                    average_daily_volume=24_000_000,
                    currency=Currency.USD,
                ),
                SampleSecurity(
                    ticker="GOOG",
                    name="Alphabet Inc. Class C",
                    country="United States",
                    sector="Communication Services",
                    market_cap=1_900_000_000_000,
                    free_float=0.88,
                    average_daily_volume=18_000_000,
                    currency=Currency.USD,
                ),
            ],
        ),
        CompanyShareClasses(
            company="Amazon",
            classes=[
                SampleSecurity(
                    ticker="AMZN",
                    name="Amazon.com Inc.",
                    country="United States",
                    sector="Consumer Discretionary",
                    market_cap=1_900_000_000_000,
                    free_float=0.90,
                    average_daily_volume=45_000_000,
                    currency=Currency.USD,
                )
            ],
        ),
        CompanyShareClasses(
            company="Apple",
            classes=[
                SampleSecurity(
                    ticker="AAPL",
                    name="Apple Inc.",
                    country="United States",
                    sector="Information Technology",
                    market_cap=3_350_000_000_000,
                    free_float=0.99,
                    average_daily_volume=95_000_000,
                    currency=Currency.USD,
                )
            ],
        ),
        CompanyShareClasses(
            company="Meta",
            classes=[
                SampleSecurity(
                    ticker="META",
                    name="Meta Platforms Inc.",
                    country="United States",
                    sector="Communication Services",
                    market_cap=1_350_000_000_000,
                    free_float=0.96,
                    average_daily_volume=25_000_000,
                    currency=Currency.USD,
                )
            ],
        ),
        CompanyShareClasses(
            company="Netflix",
            classes=[
                SampleSecurity(
                    ticker="NFLX",
                    name="Netflix Inc.",
                    country="United States",
                    sector="Communication Services",
                    market_cap=280_000_000_000,
                    free_float=0.92,
                    average_daily_volume=8_500_000,
                    currency=Currency.USD,
                )
            ],
        ),
    ]


def choose_share_class(
    classes: list[SampleSecurity],
    *,
    current_selection: str | None = None,
) -> SampleSecurity:
    """
    Apply the share-class eligibility logic from Section 2.1.2.

    If a share class is currently in the index, it may stay as long as its ADV
    is at least 75% of any other share class. Otherwise the highest ADV share
    class is selected. When no current selection is provided the most liquid
    class is chosen.
    """

    if not classes:
        raise ValueError("Company is missing share-class samples.")

    if current_selection:
        current = next((s for s in classes if s.ticker == current_selection), None)
        if current:
            max_other_adv = max(
                (s.average_daily_volume for s in classes if s.ticker != current_selection),
                default=0,
            )
            if max_other_adv == 0 or current.average_daily_volume >= 0.75 * max_other_adv:
                return current

    return max(classes, key=lambda s: s.average_daily_volume)


def select_faang_constituents(
    share_class_groups: Iterable[CompanyShareClasses],
    *,
    current_share_classes: dict[str, str] | None = None,
) -> list[Constituent]:
    """Select one share class per company and convert to constituents."""

    selected_samples: list[SampleSecurity] = []
    audit_rows: list[dict] = []

    for group in share_class_groups:
        current_choice = None
        if current_share_classes:
            current_choice = current_share_classes.get(group.company)
        chosen = choose_share_class(group.classes, current_selection=current_choice)
        selected_samples.append(chosen)
        audit_rows.append(
            {
                "company": group.company,
                "ticker": chosen.ticker,
                "share_classes": ", ".join(c.ticker for c in group.classes),
                "selected": chosen.ticker,
            }
        )

    constituents = build_constituents(selected_samples)
    print("\nSHARE-CLASS SELECTION")
    print("-" * 60)
    for row in audit_rows:
        print(f"{row['company']:<10} -> {row['selected']} " f"(candidates: {row['share_classes']})")

    return constituents


def faang_rebalancing_schedule() -> RebalancingSchedule:
    """Quarterly schedule for the FAANG indices."""

    return (
        RebalancingSchedule.builder()
        .frequency("quarterly")
        .on_months([3, 6, 9, 12])
        .on_day(15)
        .selection_date_offset(5)
        .announcement_date_offset(2)
        .build()
    )


def configure_faang_index(
    name: str,
    identifier: str,
    weighting: WeightingMethod,
    constituents: list[Constituent],
) -> Index:
    """Create and configure an Index instance."""

    tickers = [c.ticker for c in constituents]
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .regions([Region.NORTH_AMERICA])
        .countries([Country.UNITED_STATES])
        .tickers(tickers)
        .build()
    )

    selection = (
        SelectionCriteria.builder()
        .select_top(len(tickers))
        .ranking_by(Factor.MARKET_CAP)
        .apply_buffer_rules(add_threshold=len(tickers), remove_threshold=len(tickers))
        .build()
    )

    validation = (
        ValidationRules.builder()
        .min_constituents(len(tickers))
        .max_constituents(len(tickers))
        .max_single_constituent_weight(0.35)
        .build()
    )

    return (
        Index.create(
            name=name,
            identifier=identifier,
            currency=Currency.USD,
            base_date="2020-06-24",
            base_value=1_000.0,
        )
        .set_universe(universe)
        .set_selection_criteria(selection)
        .set_weighting_method(weighting)
        .set_rebalancing_schedule(faang_rebalancing_schedule())
        .set_validation_rules(validation)
    )


def main() -> None:
    """Run the FAANG example."""

    print("=" * 80)
    print("ACME FAANG Index (Guideline Demo)")
    print("=" * 80)
    print("Guideline source: ACME FAANG Series v1.1 (07-Jan-2021)")

    constituents = select_faang_constituents(faang_share_class_samples())
    print_selection_audit(
        [
            {
                "ticker": c.ticker,
                "country": c.country,
                "free_float_cap": c.free_float_market_cap,
                "cumulative_share": (i + 1) / len(constituents),
                "selected": True,
                "reason": "static-basket",
            }
            for i, c in enumerate(constituents)
        ]
    )

    cap_index = configure_faang_index(
        name="ACME FAANG Index (Demo)",
        identifier="SOFAANG",
        weighting=WeightingMethod.free_float_market_cap().build(),
        constituents=constituents,
    )
    equal_index = configure_faang_index(
        name="ACME FAANG Equal Weight Index (Demo)",
        identifier="SFAANGE",
        weighting=WeightingMethod.equal_weight(),
        constituents=constituents,
    )

    for idx, path in (
        (cap_index, CONFIG_CAP_PATH),
        (equal_index, CONFIG_EQUAL_PATH),
    ):
        report = idx.validate()
        if report.is_valid:
            print(f"\n✅ {idx.name} configuration valid.")
        else:
            print(f"\n⚠️  {idx.name} validation issues:")
            for error in report.errors:
                print(f"   - {error.severity.value}: {error.message}")
        idx.save(path.as_posix())
        print(f"   Saved configuration to {path}")

    print("\nRebalancing cadence:")
    print("  Quarterly (March, June, September, December) following the guideline.")

    print("\nSummary")
    print("-" * 80)
    print(f"Constituents: {[c.ticker for c in constituents]}")
    print(f"Cap-weight config: {CONFIG_CAP_PATH.resolve()}")
    print(f"Equal-weight config: {CONFIG_EQUAL_PATH.resolve()}")


if __name__ == "__main__":
    main()
