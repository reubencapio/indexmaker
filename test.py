import openbb

from indexforge import (
    Country,
    Currency,
    Factor,
    Index,
    RebalancingSchedule,
    Sector,
    SelectionCriteria,
    Universe,
    WeightingMethod,
)

# Create the index
index = Index.create(
    name="European ESG Dividend Aristocrats Index",
    identifier="EUESGDIV",
    currency=Currency.EUR,
    base_date="2024-05-21",
    base_value=1000,
)

# Define the universe
universe = (
    Universe.builder()
    .asset_class("EQUITIES")
    .countries(
        [
            Country.UNITED_KINGDOM,
            Country.FRANCE,
            Country.GERMANY,
            Country.SWITZERLAND,
            Country.NETHERLANDS,
            Country.SPAIN,
            Country.ITALY,
            Country.SWEDEN,
            Country.DENMARK,
        ]
    )
    .sectors(
        [
            Sector.HEALTH_CARE,
            Sector.CONSUMER_STAPLES,
            Sector.FINANCIALS,
            Sector.INDUSTRIALS,
            Sector.UTILITIES,
            Sector.MATERIALS,
            Sector.ENERGY,
            Sector.COMMUNICATION_SERVICES,
        ]
    )
    .min_market_cap(5000000000)
    .min_market_cap(5000000000)
    # [Dynamic Screening] Fetching active tickers via OpenBB
    .tickers(
        [
            t
            for t in openbb.obb.equity.discovery.active(provider="yfinance")
            .to_df()["symbol"]
            .tolist()
        ]
    )
    .build()
)

# Selection criteria
selection = (
    SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(40)
    # Filter: Minimum Dividend Yield >= 2.5%
    .custom_filter(lambda c: c.dividend_yield and c.dividend_yield >= 0.025)
    # Filter: Minimum ESG Score >= 70 (Commenting out as free data source lacks ESG scores)
    # .custom_filter(lambda c: c.esg_score and c.esg_score >= 70)
    .build()
)

# Weighting method
weighting = WeightingMethod.equal_weight()

# Rebalancing schedule
rebalancing = RebalancingSchedule.quarterly()

# Configure the index
(
    index.set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
    .set_rebalancing_schedule(rebalancing)
)

# Calculate index to populate constituents
index.calculate(index.base_date)

# Get constituents
constituents = index.get_constituents()
for c in constituents:
    print(f"{c.ticker}: {c.name} - {c.weight:.2%}")
