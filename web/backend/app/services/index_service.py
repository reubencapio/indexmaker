"""
Index service.

Business logic for index creation, calculation, and management.
Integrates with the indexmaker library for index calculations.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.index import Index, IndexComponent, IndexSnapshot, WeightingMethod
from app.services.market_data_service import MarketDataService


# Predefined universe of major stocks by country
# In production, this would come from a database or market data provider
UNIVERSE_BY_COUNTRY = {
    "US": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
        "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "PEP", "KO",
        "AVGO", "COST", "TMO", "WMT", "MCD", "CSCO", "ACN", "ABT", "DHR", "NEE",
        "LIN", "ADBE", "CRM", "NKE", "TXN", "PM", "UNP", "RTX", "HON", "IBM",
        "QCOM", "CAT", "INTC", "AMGN", "LOW", "DE", "BA", "GS", "SPGI", "INTU",
        "AMD", "AMAT", "ISRG", "AXP", "BLK", "BKNG", "MDLZ", "GILD", "ADI", "SYK",
        "VRTX", "ADP", "TJX", "PLD", "MMC", "LMT", "CI", "SLB", "MO", "ZTS",
        "PYPL", "DIS", "NOW", "SNOW", "UBER", "CRM", "SQ", "SHOP", "DDOG", "NET",
    ],
    "CA": [
        "RY", "TD", "BNS", "BMO", "CM", "ENB", "CNQ", "TRP", "CP", "CNR",
        "BCE", "T", "SU", "MFC", "ATD", "CSU", "SHOP", "WCN", "FTS", "QSR",
    ],
    "GB": [
        "SHEL", "AZN", "HSBA", "ULVR", "BP", "GSK", "RIO", "BATS", "DGE", "LSEG",
    ],
    "DE": [
        "SAP", "SIE", "ALV", "DTE", "BAS", "MRK.DE", "BMW", "VOW3", "BAYN", "ADS",
    ],
    "JP": [
        "TM", "SONY", "MUFG", "SMFG", "HMC", "NTT", "NTDOY", "MFG", "IX", "FANUY",
    ],
    "FR": [
        "MC.PA", "OR.PA", "TTE", "SAN.PA", "AIR.PA", "SU.PA", "BNP.PA", "AI.PA",
    ],
    "CH": [
        "NESN", "ROG", "NOVN", "UHR", "ZURN", "ABBN", "GIVN", "LONN",
    ],
}

# Sector mapping (simplified - in production use proper GICS codes)
SECTOR_MAPPING = {
    "technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AVGO", "CSCO", "ADBE", "CRM", "INTC", 
                   "AMD", "AMAT", "TXN", "QCOM", "IBM", "NOW", "SNOW", "DDOG", "NET", "SHOP", "SAP", "SONY"],
    "healthcare": ["UNH", "JNJ", "MRK", "ABBV", "TMO", "ABT", "DHR", "AMGN", "GILD", "ISRG", 
                   "VRTX", "SYK", "ZTS", "CI", "AZN", "GSK"],
    "financials": ["JPM", "V", "MA", "BRK-B", "GS", "BLK", "AXP", "SPGI", "MMC", "ADP",
                   "RY", "TD", "BNS", "BMO", "HSBA", "MUFG", "SMFG", "BNP.PA"],
    "consumer_discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG", "TJX", "DIS", "UBER", "SQ"],
    "consumer_staples": ["PG", "PEP", "KO", "COST", "WMT", "PM", "MO", "MDLZ", "ULVR", "NESN"],
    "industrials": ["CAT", "DE", "BA", "HON", "UNP", "RTX", "LMT", "GE", "CP", "CNR"],
    "energy": ["CVX", "XOM", "SLB", "ENB", "CNQ", "TRP", "SU", "BP", "SHEL", "TTE"],
    "materials": ["LIN", "APD", "ECL", "NEM", "FCX", "RIO", "BHP", "BAS"],
    "utilities": ["NEE", "DUK", "SO", "AEP", "D", "EXC", "FTS"],
    "real_estate": ["PLD", "AMT", "CCI", "EQIX", "PSA", "SPG"],
    "communication_services": ["GOOGL", "META", "DIS", "NFLX", "T", "VZ", "TMUS", "BCE"],
}


class IndexService:
    """
    Service for index operations.

    Handles index calculations, weight assignments, and integrates
    with the indexmaker library.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.market_data = MarketDataService()

    async def fetch_component_data(self, ticker: str) -> dict[str, Any]:
        """
        Fetch market data for a component.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with market data
        """
        data = await self.market_data.get_security_info(ticker)
        return data or {}

    async def populate_components(self, index: Index, max_components: int = 50) -> list[IndexComponent]:
        """
        Automatically populate index components based on universe criteria.
        
        Filters from predefined universe based on:
        - Countries specified in index
        - Sectors specified in index
        - Minimum market cap
        
        Then selects top N by market cap.
        
        Args:
            index: Index to populate
            max_components: Maximum components to add
            
        Returns:
            List of created components
        """
        # Build candidate ticker list from universe
        candidate_tickers = set()
        
        # Filter by countries
        countries = index.countries or list(UNIVERSE_BY_COUNTRY.keys())
        for country in countries:
            country_upper = country.upper()
            if country_upper in UNIVERSE_BY_COUNTRY:
                candidate_tickers.update(UNIVERSE_BY_COUNTRY[country_upper])
        
        # Filter by sectors if specified
        if index.sectors:
            sector_tickers = set()
            for sector in index.sectors:
                sector_lower = sector.lower().replace(" ", "_")
                if sector_lower in SECTOR_MAPPING:
                    sector_tickers.update(SECTOR_MAPPING[sector_lower])
            # Intersect with country-filtered tickers
            candidate_tickers = candidate_tickers.intersection(sector_tickers)
        
        if not candidate_tickers:
            return []
        
        # Fetch market data for all candidates and filter/sort
        candidates_with_data = []
        for ticker in candidate_tickers:
            try:
                data = await self.market_data.get_security_info(ticker)
                if data and data.get("market_cap"):
                    # Apply min market cap filter
                    if index.min_market_cap and data["market_cap"] < index.min_market_cap:
                        continue
                    candidates_with_data.append((ticker, data))
            except Exception:
                continue
        
        # Sort by market cap (descending) and take top N
        candidates_with_data.sort(key=lambda x: x[1].get("market_cap", 0), reverse=True)
        selected = candidates_with_data[:max_components]
        
        # Create components
        components = []
        for ticker, data in selected:
            component = IndexComponent(
                index_id=index.id,
                ticker=ticker,
                name=data.get("name"),
                sector=data.get("sector"),
                industry=data.get("industry"),
                country=data.get("country"),
                market_cap=data.get("market_cap"),
                price=data.get("price"),
                avg_volume=data.get("avg_volume"),
                weight=0.0,  # Will be calculated
            )
            self.db.add(component)
            components.append(component)
        
        return components

    async def calculate_index(self, index: Index) -> None:
        """
        Calculate/recalculate index values.

        Updates component prices, calculates weights based on methodology,
        and computes the current index value.

        Args:
            index: Index to calculate
        """
        if not index.components:
            return

        # Fetch current prices for all components
        for component in index.components:
            if not component.is_active:
                continue

            data = await self.market_data.get_security_info(component.ticker)
            if data:
                component.price = data.get("price")
                component.market_cap = data.get("market_cap")
                component.avg_volume = data.get("avg_volume")
                component.sector = data.get("sector")
                component.country = data.get("country")

        # Calculate weights based on methodology
        await self._calculate_weights(index)

        # Calculate index value
        await self._calculate_value(index)

        # Update last calculated timestamp
        index.last_calculated = datetime.now(timezone.utc)

    async def _calculate_weights(self, index: Index) -> None:
        """
        Calculate component weights based on weighting methodology.

        Supports:
        - Equal weight
        - Market cap
        - Free float market cap
        - Custom (via custom_rules)
        """
        active_components = [c for c in index.components if c.is_active and c.price]

        if not active_components:
            return

        method = index.weighting_method

        if method == WeightingMethod.EQUAL_WEIGHT.value:
            weight = 1.0 / len(active_components)
            for component in active_components:
                component.weight = weight

        elif method == WeightingMethod.MARKET_CAP.value:
            total_mcap = sum(c.market_cap or 0 for c in active_components)
            if total_mcap > 0:
                for component in active_components:
                    component.weight = (component.market_cap or 0) / total_mcap

        elif method == WeightingMethod.FREE_FLOAT_MARKET_CAP.value:
            # For simplicity, use market cap (would need free float data)
            total_mcap = sum(c.market_cap or 0 for c in active_components)
            if total_mcap > 0:
                for component in active_components:
                    component.weight = (component.market_cap or 0) / total_mcap

        # Apply capping rules
        await self._apply_capping(index, active_components)

    async def _apply_capping(
        self,
        index: Index,
        components: list[IndexComponent],
    ) -> None:
        """
        Apply weight capping rules.

        Iteratively caps weights and redistributes excess.
        """
        if not index.max_weight:
            return

        max_weight = index.max_weight
        iterations = 0
        max_iterations = 10

        while iterations < max_iterations:
            excess = 0.0
            uncapped_weight = 0.0
            capped_count = 0

            for component in components:
                if component.weight > max_weight:
                    excess += component.weight - max_weight
                    component.weight = max_weight
                    capped_count += 1
                else:
                    uncapped_weight += component.weight

            if excess == 0 or uncapped_weight == 0:
                break

            # Redistribute excess proportionally
            for component in components:
                if component.weight < max_weight:
                    addition = excess * (component.weight / uncapped_weight)
                    component.weight += addition

            iterations += 1

        # Normalize to ensure weights sum to 1
        total = sum(c.weight for c in components)
        if total > 0:
            for component in components:
                component.weight /= total

    async def _calculate_value(self, index: Index) -> None:
        """
        Calculate current index value.

        Uses a simple price-weighted approach relative to base value.
        """
        active_components = [c for c in index.components if c.is_active and c.price]

        if not active_components:
            return

        # Calculate weighted return contribution
        # For a proper index, we'd track shares and use divisor methodology
        # This is a simplified version for demonstration

        weighted_value = 0.0
        for component in active_components:
            weighted_value += (component.price or 0) * component.weight

        # Normalize to base value (simplified)
        # In reality, you'd track shares and use a proper divisor
        index.current_value = weighted_value

    async def create_snapshot(self, index: Index) -> IndexSnapshot:
        """
        Create a historical snapshot of the index.

        Args:
            index: Index to snapshot

        Returns:
            Created snapshot
        """
        # Calculate daily return if there's a previous snapshot
        daily_return = None
        if index.snapshots:
            prev_value = index.snapshots[0].value
            if prev_value and index.current_value:
                daily_return = (index.current_value - prev_value) / prev_value

        snapshot = IndexSnapshot(
            index_id=index.id,
            date=datetime.now(timezone.utc),
            value=index.current_value or index.base_value,
            daily_return=daily_return,
            component_weights={
                c.ticker: c.weight for c in index.components if c.is_active
            },
        )

        self.db.add(snapshot)
        return snapshot

    async def rebalance_index(self, index: Index) -> None:
        """
        Perform index rebalancing.

        Recalculates weights and creates a rebalance snapshot.
        """
        await self.calculate_index(index)

        snapshot = await self.create_snapshot(index)
        snapshot.is_rebalance_day = True

