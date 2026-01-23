#!/usr/bin/env python3
"""
Indexmaker Subscription Economy Performance Index Example
=============================================================

This script demonstrates how to configure the Indexmaker Subscription Economy
Performance-Index using LIVE data from Yahoo Finance.

Features implemented from the guideline:
* Universe: Developed market equities with subscription economy exposure
* Sectors: IaaS (5), SaaS (8), Billing (2), XaaS (10) = 25 total components
* Market cap minimum: USD 750 million
* ADTV minimum: USD 1 million (3-month average)
* Financial scoring: FCF, Revenue Growth, R&D/Sales, GPM, Cash
* Equal weighting (4% per component)
* Semi-annual rebalancing (second Wednesday in March and September)

Run with: python examples/subscription_economy.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from indexforge import (
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
from indexforge.data.connectors.yahoo import YahooFinanceConnector

logging.basicConfig(level=logging.WARNING)
CONFIG_PATH = Path("subscription_economy.json")


class SubscriptionSector(str, Enum):
    """Subscription economy sectors per the guideline."""

    IAAS = "Infrastructure-as-a-Service"
    SAAS = "Software-as-a-Service"
    BILLING = "Subscription Management (Billing)"
    XAAS = "X-as-a-Service"

    def __str__(self) -> str:
        return self.value


# Target sector distribution per guideline Section 2.2
SECTOR_DISTRIBUTION: dict[SubscriptionSector, int] = {
    SubscriptionSector.IAAS: 5,
    SubscriptionSector.SAAS: 8,
    SubscriptionSector.BILLING: 2,
    SubscriptionSector.XAAS: 10,
}

TOTAL_COMPONENTS = sum(SECTOR_DISTRIBUTION.values())  # 25

# Sector classification for subscription economy stocks
# This mapping would typically come from a thematic data provider
TICKER_SECTOR_MAP: dict[str, SubscriptionSector] = {
    # IaaS
    "AMZN": SubscriptionSector.IAAS,
    "MSFT": SubscriptionSector.IAAS,
    "GOOGL": SubscriptionSector.IAAS,
    "ORCL": SubscriptionSector.IAAS,
    "IBM": SubscriptionSector.IAAS,
    # SaaS
    "CRM": SubscriptionSector.SAAS,
    "ADBE": SubscriptionSector.SAAS,
    "NOW": SubscriptionSector.SAAS,
    "INTU": SubscriptionSector.SAAS,
    "WDAY": SubscriptionSector.SAAS,
    "TEAM": SubscriptionSector.SAAS,
    "HUBS": SubscriptionSector.SAAS,
    "ZM": SubscriptionSector.SAAS,
    "DDOG": SubscriptionSector.SAAS,
    "SNOW": SubscriptionSector.SAAS,
    # Billing
    "ZUO": SubscriptionSector.BILLING,
    "BILL": SubscriptionSector.BILLING,
    # XaaS
    "NFLX": SubscriptionSector.XAAS,
    "DIS": SubscriptionSector.XAAS,
    "SPOT": SubscriptionSector.XAAS,
    "UBER": SubscriptionSector.XAAS,
    "LYFT": SubscriptionSector.XAAS,
    "SHOP": SubscriptionSector.XAAS,
    "SE": SubscriptionSector.XAAS,
    "BABA": SubscriptionSector.XAAS,
    "ABNB": SubscriptionSector.XAAS,
    "DASH": SubscriptionSector.XAAS,
    "RBLX": SubscriptionSector.XAAS,
    "U": SubscriptionSector.XAAS,
}


@dataclass(slots=True)
class ScoredSecurity:
    """Security with subscription economy attributes and financial score."""

    ticker: str
    name: str
    country: str
    sector: SubscriptionSector
    market_cap: float
    free_float_factor: float
    adtv: float
    currency: Currency
    # Financial key figures
    fcf: float
    revenue_growth: float
    rd_sales: float
    gpm: float
    cash: float
    # Computed score
    score: int = 0


def score_fcf(fcf: float) -> int:
    """Score Free Cash Flow per guideline table (in millions USD)."""
    thresholds = [
        (10_000, 250),
        (8_000, 200),
        (6_000, 180),
        (4_000, 160),
        (2_000, 140),
        (1_000, 130),
        (500, 120),
        (200, 110),
        (100, 100),
        (90, 90),
        (80, 80),
        (70, 70),
        (60, 60),
        (50, 50),
        (40, 40),
        (30, 30),
        (20, 20),
        (10, 10),
    ]
    for threshold, score in thresholds:
        if fcf > threshold:
            return score
    return 0


def score_revenue_growth(rg: float) -> int:
    """Score Revenue Growth per guideline table (%)."""
    thresholds = [
        (200, 200),
        (150, 180),
        (100, 160),
        (70, 140),
        (60, 120),
        (50, 100),
        (40, 80),
        (30, 60),
        (20, 40),
        (10, 20),
    ]
    for threshold, score in thresholds:
        if rg > threshold:
            return score
    return 0


def score_rd_sales(rd: float) -> int:
    """Score R&D/Sales per guideline table (%)."""
    thresholds = [
        (30, 50),
        (20, 40),
        (10, 30),
        (5, 20),
    ]
    for threshold, score in thresholds:
        if rd > threshold:
            return score
    return 0


def score_gpm(gpm: float) -> int:
    """Score Gross Profit Margin per guideline table (%)."""
    thresholds = [
        (85, 150),
        (80, 100),
        (75, 60),
        (70, 40),
        (60, 30),
        (50, 20),
        (40, 10),
    ]
    for threshold, score in thresholds:
        if gpm > threshold:
            return score
    return 0


def score_cash(cash: float) -> int:
    """Score Cash position per guideline table (in millions USD)."""
    thresholds = [
        (10_000, 50),
        (5_000, 40),
        (2_000, 30),
        (500, 20),
        (200, 10),
    ]
    for threshold, score in thresholds:
        if cash > threshold:
            return score
    return 0


def compute_financial_score(sec: ScoredSecurity) -> int:
    """Compute the overall financial score per Section 2.2."""
    return (
        score_fcf(sec.fcf)
        + score_revenue_growth(sec.revenue_growth)
        + score_rd_sales(sec.rd_sales)
        + score_gpm(sec.gpm)
        + score_cash(sec.cash)
    )


def fetch_fundamentals_from_yahoo(ticker: str) -> dict:
    """
    Fetch financial fundamentals from Yahoo Finance.

    Returns dict with: fcf, revenue_growth, rd_sales, gpm, cash
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info
        financials = stock.financials
        cash_flow = stock.cashflow

        # Free Cash Flow (in millions)
        fcf = 0.0
        if cash_flow is not None and not cash_flow.empty:
            if "Free Cash Flow" in cash_flow.index:
                fcf = float(cash_flow.loc["Free Cash Flow"].iloc[0] or 0) / 1_000_000

        # Revenue Growth (%)
        revenue_growth = 0.0
        if financials is not None and not financials.empty:
            if "Total Revenue" in financials.index and len(financials.columns) >= 2:
                rev_current = float(financials.loc["Total Revenue"].iloc[0] or 0)
                rev_prev = float(financials.loc["Total Revenue"].iloc[1] or 0)
                if rev_prev > 0:
                    revenue_growth = ((rev_current - rev_prev) / rev_prev) * 100

        # R&D / Sales (%)
        rd_sales = 0.0
        if financials is not None and not financials.empty:
            rd = 0.0
            if "Research And Development" in financials.index:
                rd = float(financials.loc["Research And Development"].iloc[0] or 0)
            elif "Research Development" in financials.index:
                rd = float(financials.loc["Research Development"].iloc[0] or 0)
            if "Total Revenue" in financials.index:
                rev = float(financials.loc["Total Revenue"].iloc[0] or 0)
                if rev > 0:
                    rd_sales = (rd / rev) * 100

        # Gross Profit Margin (%)
        gpm = float(info.get("grossMargins", 0) or 0) * 100

        # Cash (in millions)
        cash = float(info.get("totalCash", 0) or 0) / 1_000_000

        return {
            "fcf": fcf,
            "revenue_growth": revenue_growth,
            "rd_sales": rd_sales,
            "gpm": gpm,
            "cash": cash,
        }
    except Exception as e:
        print(f"  Warning: Could not fetch fundamentals for {ticker}: {e}")
        return {"fcf": 0, "revenue_growth": 0, "rd_sales": 0, "gpm": 0, "cash": 0}


def fetch_universe_from_yahoo(tickers: list[str]) -> list[ScoredSecurity]:
    """
    Fetch universe data from Yahoo Finance using the library's connector.

    Combines basic constituent data with additional fundamentals for scoring.
    """
    print("\nFetching data from Yahoo Finance...")
    connector = YahooFinanceConnector()

    # Get basic constituent data
    constituents = connector.get_constituent_data(tickers)

    securities: list[ScoredSecurity] = []

    for c in constituents:
        # Skip if not in our sector map or doesn't meet minimum requirements
        if c.ticker not in TICKER_SECTOR_MAP:
            continue

        # Check minimum market cap (USD 750M)
        if c.market_cap < 750_000_000:
            print(f"  Skipping {c.ticker}: market cap ${c.market_cap/1e9:.1f}B < $0.75B")
            continue

        # Fetch fundamentals for scoring
        print(f"  Fetching fundamentals for {c.ticker}...")
        fundamentals = fetch_fundamentals_from_yahoo(c.ticker)

        sec = ScoredSecurity(
            ticker=c.ticker,
            name=c.name,
            country=c.country,
            sector=TICKER_SECTOR_MAP[c.ticker],
            market_cap=c.market_cap,
            free_float_factor=c.free_float_factor,
            adtv=c.average_daily_volume,
            currency=c.currency,
            fcf=fundamentals["fcf"],
            revenue_growth=fundamentals["revenue_growth"],
            rd_sales=fundamentals["rd_sales"],
            gpm=fundamentals["gpm"],
            cash=fundamentals["cash"],
        )
        sec.score = compute_financial_score(sec)
        securities.append(sec)

    return securities


def select_components(
    universe: list[ScoredSecurity],
) -> tuple[list[ScoredSecurity], list[dict]]:
    """
    Select 25 components per guideline distribution.

    1. Score each security (already done)
    2. Rank by score within sector
    3. Select top N per sector
    """
    # Group by sector
    by_sector: dict[SubscriptionSector, list[ScoredSecurity]] = {}
    for sec in universe:
        by_sector.setdefault(sec.sector, []).append(sec)

    # Sort each sector by score descending
    for sector in by_sector:
        by_sector[sector].sort(key=lambda x: x.score, reverse=True)

    # Select top N per sector
    selected: list[ScoredSecurity] = []
    audit_rows: list[dict] = []

    for sector, count in SECTOR_DISTRIBUTION.items():
        candidates = by_sector.get(sector, [])
        for i, sec in enumerate(candidates):
            is_selected = i < count
            audit_rows.append(
                {
                    "ticker": sec.ticker,
                    "name": sec.name,
                    "sector": str(sector),
                    "score": sec.score,
                    "rank": i + 1,
                    "selected": is_selected,
                    "reason": f"top-{count} in {sector.name}" if is_selected else "outside-quota",
                }
            )
            if is_selected:
                selected.append(sec)

    return selected, audit_rows


def build_constituents(securities: list[ScoredSecurity]) -> list[Constituent]:
    """Convert selected securities to Constituent objects."""
    return [
        Constituent(
            ticker=sec.ticker,
            name=sec.name,
            country=sec.country,
            sector=str(sec.sector),
            market_cap=sec.market_cap,
            free_float_factor=sec.free_float_factor,
            free_float_market_cap=sec.market_cap * sec.free_float_factor,
            average_daily_volume=sec.adtv,
            currency=sec.currency,
        )
        for sec in securities
    ]


def subscription_economy_rebalancing() -> RebalancingSchedule:
    """
    Semi-annual rebalancing on second Wednesday in March and September.
    Selection Day is 10 calculation days prior.
    """
    return (
        RebalancingSchedule.builder()
        .frequency("semi_annual")
        .on_months([3, 9])
        .on_day(14)  # Approx second Wednesday
        .selection_date_offset(10)
        .announcement_date_offset(5)
        .build()
    )


def configure_index(constituents: list[Constituent]) -> Index:
    """Configure the Indexmaker Subscription Economy Performance Index."""
    tickers = [c.ticker for c in constituents]

    # Developed markets universe per guideline Section 2.1
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .regions([Region.GLOBAL])
        .countries(
            [
                Country.AUSTRALIA,
                Country.AUSTRIA,
                Country.BELGIUM,
                Country.DENMARK,
                Country.FINLAND,
                Country.FRANCE,
                Country.GERMANY,
                Country.HONG_KONG,
                Country.IRELAND,
                Country.ITALY,
                Country.JAPAN,
                Country.SOUTH_KOREA,
                Country.NETHERLANDS,
                Country.NORWAY,
                Country.NEW_ZEALAND,
                Country.PORTUGAL,
                Country.SINGAPORE,
                Country.SPAIN,
                Country.SWEDEN,
                Country.SWITZERLAND,
                Country.UNITED_KINGDOM,
                Country.UNITED_STATES,
            ]
        )
        .tickers(tickers)
        .min_market_cap(750_000_000, currency=Currency.USD)
        .min_average_daily_volume(1_000_000)
        .min_free_float(0.1)
        .build()
    )

    # Selection based on financial score ranking within sectors
    selection = (
        SelectionCriteria.builder()
        .ranking_by(Factor.MARKET_CAP)  # Placeholder; actual scoring is custom
        .select_top(TOTAL_COMPONENTS)
        .build()
    )

    # Equal weighting: 4% per component (1/25)
    weighting = WeightingMethod.equal_weight()

    rebalancing = subscription_economy_rebalancing()

    validation = (
        ValidationRules.builder()
        .min_constituents(20)  # Allow some flexibility for live data
        .max_constituents(30)
        .max_single_constituent_weight(0.05)
        .max_single_sector_weight(0.45)
        .build()
    )

    return (
        Index.create(
            name="Indexmaker Subscription Economy Performance-Index (Demo)",
            identifier="SOSUBEC",
            currency=Currency.USD,
            base_date="2020-01-31",
            base_value=100.0,
        )
        .set_universe(universe)
        .set_selection_criteria(selection)
        .set_weighting_method(weighting)
        .set_rebalancing_schedule(rebalancing)
        .set_validation_rules(validation)
    )


def print_selection_audit(audit_rows: list[dict]) -> None:
    """Print detailed selection audit."""
    print("\nFINANCIAL SCORE SELECTION AUDIT")
    print("-" * 90)
    print(f"{'Ticker':<10} {'Name':<30} {'Sector':<12} {'Score':>6} {'Rank':>5} {'Selected'}")
    print("-" * 90)

    current_sector = None
    for row in sorted(audit_rows, key=lambda r: (r["sector"], -r["score"])):
        if row["sector"] != current_sector:
            current_sector = row["sector"]
            print(f"\n[{current_sector}]")
        mark = "✓" if row["selected"] else ""
        print(
            f"{row['ticker']:<10} {row['name'][:28]:<30} "
            f"{row['score']:>6} {row['rank']:>5}   {mark}"
        )


def print_sector_distribution(selected: list[ScoredSecurity]) -> None:
    """Print sector distribution summary."""
    print("\nSECTOR DISTRIBUTION")
    print("-" * 50)
    counts: dict[SubscriptionSector, int] = {}
    for sec in selected:
        counts[sec.sector] = counts.get(sec.sector, 0) + 1

    total_selected = len(selected)
    for sector, target in SECTOR_DISTRIBUTION.items():
        actual = counts.get(sector, 0)
        status = "✓" if actual == target else f"({actual}/{target})"
        weight = (actual / max(total_selected, 1)) * 100
        print(f"{sector.name:<10} {actual:>2}/{target:<2} ({weight:>5.1f}%)  {status}")


def main() -> None:
    """Run the Subscription Economy example with live data."""
    print("=" * 80)
    print("Indexmaker Subscription Economy Performance-Index (Guideline Demo)")
    print("=" * 80)
    print("Guideline source: Indexmaker SOSUBEC v1.1 (08-Dec-2022)")
    print("Strategy: Subscription economy thematic equity index")
    print(f"Target: {TOTAL_COMPONENTS} components, equal-weighted (4% each)")
    print("\nData source: Yahoo Finance (LIVE)")

    # Get all tickers from our sector map
    tickers = list(TICKER_SECTOR_MAP.keys())

    # Fetch live data from Yahoo Finance
    universe = fetch_universe_from_yahoo(tickers)

    print(f"\nUniverse size: {len(universe)} securities (after filtering)")

    if len(universe) < 10:
        print("\n⚠️  Not enough securities fetched. Check network connection.")
        return

    # Select components based on scores
    selected, audit_rows = select_components(universe)

    print(f"Selected: {len(selected)} components")

    print_selection_audit(audit_rows)
    print_sector_distribution(selected)

    # Build constituents and configure index
    constituents = build_constituents(selected)
    index = configure_index(constituents)

    report = index.validate()
    if not report.is_valid:
        print("\n⚠️  Validation issues detected:")
        for issue in report.errors:
            print(f"   - {issue.severity.value}: {issue.message}")
    else:
        print("\n✅ Index configuration passes validation rules.")

    index.save(CONFIG_PATH.as_posix())
    print(f"✅ Configuration saved to {CONFIG_PATH}")

    print("\nRebalancing cadence:")
    print("  Semi-annual (March and September, second Wednesday)")
    print("  Selection Day: 10 calculation days prior to Rebalance Day")

    print("\nSummary")
    print("-" * 80)
    print(f"Name:        {index.name}")
    print(f"Identifier:  {index.identifier}")
    print(f"Currency:    {index.currency}")
    print("Base Date:   2020-01-31")
    print("Base Value:  100")
    print(f"Components:  {len(constituents)} (equal-weighted @ 4% each)")
    print(f"Weighting:   {index.weighting_method.scheme}")
    print(f"Saved file:  {CONFIG_PATH.resolve()}")


if __name__ == "__main__":
    main()
