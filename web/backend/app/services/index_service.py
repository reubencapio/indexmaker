"""
Index service.

Business logic for index creation, calculation, and management.
Integrates with the indexforge library for index calculations.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.index import Index, IndexComponent, IndexSnapshot, WeightingMethod
from app.services import index_math
from app.services.index_math import Holding, IndexMathError
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

# Predefined universe of major stocks by country
# In production, this would come from a database or market data provider
UNIVERSE_BY_COUNTRY = {
    "US": [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "NVDA",
        "META",
        "TSLA",
        "BRK-B",
        "UNH",
        "JNJ",
        "JPM",
        "V",
        "PG",
        "MA",
        "HD",
        "CVX",
        "MRK",
        "ABBV",
        "PEP",
        "KO",
        "AVGO",
        "COST",
        "TMO",
        "WMT",
        "MCD",
        "CSCO",
        "ACN",
        "ABT",
        "DHR",
        "NEE",
        "LIN",
        "ADBE",
        "CRM",
        "NKE",
        "TXN",
        "PM",
        "UNP",
        "RTX",
        "HON",
        "IBM",
        "QCOM",
        "CAT",
        "INTC",
        "AMGN",
        "LOW",
        "DE",
        "BA",
        "GS",
        "SPGI",
        "INTU",
        "AMD",
        "AMAT",
        "ISRG",
        "AXP",
        "BLK",
        "BKNG",
        "MDLZ",
        "GILD",
        "ADI",
        "SYK",
        "VRTX",
        "ADP",
        "TJX",
        "PLD",
        "MMC",
        "LMT",
        "CI",
        "SLB",
        "MO",
        "ZTS",
        "PYPL",
        "DIS",
        "NOW",
        "SNOW",
        "UBER",
        "CRM",
        "SQ",
        "SHOP",
        "DDOG",
        "NET",
    ],
    "CA": [
        "RY",
        "TD",
        "BNS",
        "BMO",
        "CM",
        "ENB",
        "CNQ",
        "TRP",
        "CP",
        "CNR",
        "BCE",
        "T",
        "SU",
        "MFC",
        "ATD",
        "CSU",
        "SHOP",
        "WCN",
        "FTS",
        "QSR",
    ],
    "GB": [
        "SHEL",
        "AZN",
        "HSBA",
        "ULVR",
        "BP",
        "GSK",
        "RIO",
        "BATS",
        "DGE",
        "LSEG",
    ],
    "DE": [
        "SAP",
        "SIE",
        "ALV",
        "DTE",
        "BAS",
        "MRK.DE",
        "BMW",
        "VOW3",
        "BAYN",
        "ADS",
    ],
    "JP": [
        "TM",
        "SONY",
        "MUFG",
        "SMFG",
        "HMC",
        "NTT",
        "NTDOY",
        "MFG",
        "IX",
        "FANUY",
    ],
    "FR": [
        "MC.PA",
        "OR.PA",
        "TTE",
        "SAN.PA",
        "AIR.PA",
        "SU.PA",
        "BNP.PA",
        "AI.PA",
    ],
    "CH": [
        "NESN",
        "ROG",
        "NOVN",
        "UHR",
        "ZURN",
        "ABBN",
        "GIVN",
        "LONN",
    ],
}

# Sector mapping (simplified - in production use proper GICS codes)
SECTOR_MAPPING = {
    "technology": [
        "AAPL",
        "MSFT",
        "GOOGL",
        "NVDA",
        "META",
        "AVGO",
        "CSCO",
        "ADBE",
        "CRM",
        "INTC",
        "AMD",
        "AMAT",
        "TXN",
        "QCOM",
        "IBM",
        "NOW",
        "SNOW",
        "DDOG",
        "NET",
        "SHOP",
        "SAP",
        "SONY",
    ],
    "healthcare": [
        "UNH",
        "JNJ",
        "MRK",
        "ABBV",
        "TMO",
        "ABT",
        "DHR",
        "AMGN",
        "GILD",
        "ISRG",
        "VRTX",
        "SYK",
        "ZTS",
        "CI",
        "AZN",
        "GSK",
    ],
    "financials": [
        "JPM",
        "V",
        "MA",
        "BRK-B",
        "GS",
        "BLK",
        "AXP",
        "SPGI",
        "MMC",
        "ADP",
        "RY",
        "TD",
        "BNS",
        "BMO",
        "HSBA",
        "MUFG",
        "SMFG",
        "BNP.PA",
    ],
    "consumer_discretionary": [
        "AMZN",
        "TSLA",
        "HD",
        "MCD",
        "NKE",
        "LOW",
        "BKNG",
        "TJX",
        "DIS",
        "UBER",
        "SQ",
    ],
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
    with the indexforge library.
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

    async def populate_components(
        self, index: Index, max_components: int = 50
    ) -> list[IndexComponent]:
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

                # Check if valid data returned
                if not data or not data.get("market_cap"):
                    continue

                # Apply min market cap filter
                if index.min_market_cap and data["market_cap"] < index.min_market_cap:
                    continue

                # Apply custom rules (Dividend, ESG)
                if index.custom_rules:
                    # Dividend Yield Filter
                    min_yield = index.custom_rules.get("min_dividend_yield")
                    if min_yield is not None:
                        current_yield = data.get("dividend_yield")
                        if current_yield is None or current_yield < min_yield:
                            continue

                    # ESG Score Filter
                    # Note: YFinance often lacks free ESG data, so we may be lenient or skip if missing
                    # For now, strict if data exists, valid if data missing (to avoid empty indices)
                    min_esg = index.custom_rules.get("min_esg_score")
                    if min_esg is not None:
                        # TODO: Fetch real ESG score when provider available
                        # current_esg = data.get("esg_score")
                        # if current_esg and current_esg < min_esg: continue
                        pass

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

        # Establish holdings on the first calculation, then hold shares fixed. The
        # weights that follow are derived from prices, never assigned: reassigning
        # them on every calculation is what used to make the level jump.
        if not self._is_initialised(index):
            self._start_index(index)
        else:
            self._refresh_level(index)

        # Update last calculated timestamp
        index.last_calculated = datetime.now(timezone.utc)

    def _holdings(self, index: Index) -> list[Holding]:
        """Priceable active constituents as index-math holdings."""
        return [
            Holding(ticker=c.ticker, price=c.price, shares=c.shares)
            for c in index.components
            if c.is_active and c.price and c.price > 0
        ]

    def _is_initialised(self, index: Index) -> bool:
        """True once the index has a divisor and share counts to value."""
        if not index.divisor or index.divisor <= 0:
            return False
        return any(c.is_active and c.shares for c in index.components)

    def _start_index(self, index: Index) -> None:
        """
        Set the opening holdings and divisor so the index starts at its base value.

        Target weights come from the methodology; from here on they are an output.
        """
        target_weights = self._target_weights(index)
        prices = {
            c.ticker: c.price for c in index.components if c.is_active and c.price and c.price > 0
        }

        try:
            holdings, divisor = index_math.inception(
                target_weights=target_weights,
                prices=prices,
                base_value=index.base_value,
            )
        except IndexMathError:
            logger.exception("Could not start index %s", index.id)
            return

        self._write_back(index, holdings, divisor)

    def _refresh_level(self, index: Index) -> None:
        """Reprice the existing holdings. Shares are fixed; weights drift."""
        holdings = self._holdings(index)
        if not holdings:
            return

        try:
            index.current_value = index_math.index_level(holdings, index.divisor)
        except IndexMathError:
            logger.exception("Could not value index %s", index.id)
            return

        self._write_weights(index, index_math.weights(holdings))

    def _write_back(self, index: Index, holdings: list[Holding], divisor: float) -> None:
        """Persist holdings, divisor, level and derived weights onto the ORM objects."""
        by_ticker = {h.ticker: h for h in holdings}
        index.divisor = divisor
        index.current_value = index_math.index_level(holdings, divisor)

        for component in index.components:
            holding = by_ticker.get(component.ticker)
            if holding is None:
                if component.is_active:
                    component.shares = 0.0
                    component.weight = 0.0
                continue
            component.shares = holding.shares

        self._write_weights(index, index_math.weights(holdings))

    def _write_weights(self, index: Index, computed: dict[str, float]) -> None:
        for component in index.components:
            if component.is_active:
                component.weight = computed.get(component.ticker, 0.0)

    def _target_weights(self, index: Index) -> dict[str, float]:
        """
        Target weights from the methodology, as they would be set at a rebalance.

        This returns weights rather than assigning them. Live weights are derived
        from prices between rebalances; these are only the aiming point applied when
        the index is started or rebalanced.

        Supports:
        - Equal weight
        - Market cap
        - Free float market cap
        - Custom (via custom_rules)
        """
        active_components = [c for c in index.components if c.is_active and c.price and c.price > 0]

        if not active_components:
            return {}

        method = index.weighting_method
        targets: dict[str, float] = {}

        if method == WeightingMethod.MARKET_CAP.value or (
            # Free float market cap needs free float data the connectors do not
            # supply yet, so it falls back to full market cap.
            method
            == WeightingMethod.FREE_FLOAT_MARKET_CAP.value
        ):
            total_mcap = sum(c.market_cap or 0 for c in active_components)
            if total_mcap > 0:
                targets = {c.ticker: (c.market_cap or 0) / total_mcap for c in active_components}

        if not targets:
            # Equal weight, and the fallback whenever the weighting data is missing:
            # an index with no usable market caps is still better equal-weighted than
            # left with every weight at zero.
            weight = 1.0 / len(active_components)
            targets = {c.ticker: weight for c in active_components}

        return self._apply_capping(index, targets)

    def _apply_capping(
        self,
        index: Index,
        targets: dict[str, float],
    ) -> dict[str, float]:
        """
        Apply weight capping rules, iteratively redistributing the excess.

        A cap below 1/n is unsatisfiable -- every name would have to sit under the
        cap and still sum to one -- so in that case the capping is skipped rather
        than silently returning weights that breach it.
        """
        if not index.max_weight or not targets:
            return targets

        max_weight = index.max_weight
        if max_weight * len(targets) < 1.0:
            logger.warning(
                "Index %s caps weights at %.4f, unreachable across %d constituents; "
                "leaving weights uncapped",
                index.id,
                max_weight,
                len(targets),
            )
            return targets

        capped = dict(targets)
        for _ in range(10):
            excess = 0.0
            uncapped_total = 0.0

            for ticker, weight in capped.items():
                if weight > max_weight:
                    excess += weight - max_weight
                    capped[ticker] = max_weight
                else:
                    uncapped_total += weight

            if excess <= 0 or uncapped_total <= 0:
                break

            for ticker, weight in capped.items():
                if weight < max_weight:
                    capped[ticker] = weight + excess * (weight / uncapped_total)

        total = sum(capped.values())
        if total > 0:
            capped = {ticker: weight / total for ticker, weight in capped.items()}

        return capped

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
            component_weights={c.ticker: c.weight for c in index.components if c.is_active},
        )

        self.db.add(snapshot)
        return snapshot

    async def rebalance_index(self, index: Index) -> None:
        """
        Perform index rebalancing.

        Reprices first, then reallocates to the methodology's target weights and
        resets the divisor so the level is continuous across the event. A rebalance
        reallocates the portfolio; it must not itself produce a return.
        """
        await self.calculate_index(index)

        holdings = self._holdings(index)
        if holdings and index.divisor:
            prices = {h.ticker: h.price for h in holdings}
            try:
                new_holdings, new_divisor = index_math.rebalance(
                    current=holdings,
                    target_weights=self._target_weights(index),
                    prices=prices,
                    divisor=index.divisor,
                )
                self._write_back(index, new_holdings, new_divisor)
            except IndexMathError:
                logger.exception("Could not rebalance index %s; holdings left as-is", index.id)

        snapshot = await self.create_snapshot(index)
        snapshot.is_rebalance_day = True
