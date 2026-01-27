from indexforge import (
    AssetClass,
    Country,
    Currency,
    DataProvider,
    Factor,
    Index,
    RebalancingSchedule,
    SelectionCriteria,
    Universe,
    WeightingMethod,
)
from indexforge.data.connectors.openbb import OpenBBConnector

print("Initializing OpenBB Connector...")
# Initialize OpenBB connector (uses yfinance as backend provider for prices)
obb_connector = OpenBBConnector(provider="yfinance")
provider = DataProvider(connectors={"openbb": obb_connector}, default_connector="openbb")

print("Searching for 'Quantum' stocks via OpenBB...")
# Use OpenBB to discover tickers matching "Quantum"
# Note: We use the 'search_stocks' method of the connector directly
# This uses 'obb.equity.search(query)' under the hood
search_results = obb_connector.search_stocks(query="Quantum", limit=20)

discovered_tickers = [item["symbol"] for item in search_results if "symbol" in item]

# Filter out some known non-equity/irrelevant ones if needed, or take top N
# For this demo, we'll take the ones found.
if not discovered_tickers:
    print("No tickers found via search. Fallback to known list for demo.")
    discovered_tickers = ["IBM", "GOOGL", "MSFT", "IONQ", "RGTI", "QUBT", "HON", "INTC", "NVDA"]
else:
    print(f"Found {len(discovered_tickers)} tickers: {discovered_tickers}")

# Create the index
index = Index.create(
    name="US Quantum Computing Index",
    identifier="USQUANTUM",
    currency=Currency.USD,
    base_date="2024-05-21",
    base_value=1000,
)

# Define the universe using the DISCOVERED tickers
universe = (
    Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .countries([Country.UNITED_STATES])
    .tickers(discovered_tickers)
    .build()
)

# Selection criteria
selection = SelectionCriteria.builder().ranking_by(Factor.MARKET_CAP).select_top(10).build()

# Weighting method
weighting = WeightingMethod.equal_weight()

# Rebalancing schedule
rebalancing = RebalancingSchedule.quarterly()

# Configure the index with OpenBB provider
(
    index.set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
    .set_rebalancing_schedule(rebalancing)
    .set_data_provider(provider)
)

print("\nFetching data and calculating index...")
index.calculate(date="2024-05-21")

# Get constituents
constituents = index.get_constituents()
print(f"\nConstituents ({len(constituents)}):")
print("-" * 50)
print(f"{'Ticker':<8} {'Weight':<10} {'Market Cap':<15} {'Name'}")
print("-" * 50)
for c in constituents:
    mcap = f"${c.market_cap:,.0f}" if c.market_cap else "N/A"
    print(f"{c.ticker:<8} {c.weight:<10.2%} {mcap:<15} {c.name[:30]}")
