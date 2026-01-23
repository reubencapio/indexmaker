"""
Universe model defining the investment universe for an index.

The universe defines which securities are eligible for inclusion in an index.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Union

from indexforge.core.constituent import Constituent
from indexforge.core.types import AssetClass, Country, Currency, Region, Sector


@dataclass
class ESGScreening:
    """ESG screening criteria for universe filtering."""

    min_esg_score: Optional[float] = None
    min_environmental_score: Optional[float] = None
    min_social_score: Optional[float] = None
    min_governance_score: Optional[float] = None
    exclude_controversial_weapons: bool = False
    exclude_tobacco: bool = False
    exclude_thermal_coal: bool = False
    exclude_gambling: bool = False
    exclude_adult_entertainment: bool = False
    exclude_alcohol: bool = False
    exclude_nuclear: bool = False
    exclude_gmo: bool = False


@dataclass
class Universe:
    """
    Defines the investment universe for an index.

    The universe specifies which securities are eligible for inclusion
    based on criteria such as asset class, region, market cap, and more.

    Attributes:
        asset_class: Type of assets (e.g., EQUITIES)
        regions: Geographic regions to include
        sectors: Industry sectors to include
        tickers: Specific tickers to include (for static universe)
        min_market_cap: Minimum market capitalization
        min_average_daily_volume: Minimum trading volume
        min_free_float: Minimum free-float ratio
        esg_screening: ESG filtering criteria

    Example:
        >>> universe = (Universe.builder()
        ...     .asset_class(AssetClass.EQUITIES)
        ...     .regions([Region.NORTH_AMERICA])
        ...     .min_market_cap(1_000_000_000)
        ...     .build()
        ... )
    """

    asset_class: AssetClass = AssetClass.EQUITIES
    regions: list[Region] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    exclude_countries: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    exclude_sectors: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    exchanges: list[str] = field(default_factory=list)

    # Specific tickers (for static universe)
    tickers: list[str] = field(default_factory=list)

    # Size and liquidity filters
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    min_average_daily_volume: Optional[float] = None
    min_free_float: Optional[float] = None

    # Currency
    currency: Currency = Currency.USD

    # ESG screening
    esg_screening: Optional[ESGScreening] = None

    # Custom filters
    custom_filters: list[Callable[[Constituent], bool]] = field(default_factory=list)

    @staticmethod
    def builder() -> "UniverseBuilder":
        """Create a new UniverseBuilder for fluent construction."""
        return UniverseBuilder()

    @staticmethod
    def from_tickers(tickers: list[str], currency: Currency = Currency.USD) -> "Universe":
        """
        Create a universe from a specific list of tickers.

        Args:
            tickers: List of ticker symbols
            currency: Currency for valuation

        Returns:
            Universe with specified tickers

        Example:
            >>> universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL"])
        """
        return Universe(
            asset_class=AssetClass.EQUITIES,
            tickers=tickers,
            currency=currency,
        )

    def is_eligible(self, constituent: Constituent) -> bool:
        """
        Check if a constituent meets the universe eligibility criteria.

        Args:
            constituent: The constituent to check

        Returns:
            True if eligible, False otherwise
        """
        # If tickers are specified, only allow those
        if self.tickers and constituent.ticker not in self.tickers:
            return False

        # Country filtering
        if self.countries and constituent.country not in self.countries:
            return False
        if self.exclude_countries and constituent.country in self.exclude_countries:
            return False

        # Sector filtering
        if self.sectors and constituent.sector not in self.sectors:
            return False
        if self.exclude_sectors and constituent.sector in self.exclude_sectors:
            return False

        # Industry filtering
        if self.industries and constituent.industry not in self.industries:
            return False

        # Market cap filtering
        if self.min_market_cap is not None and constituent.market_cap < self.min_market_cap:
            return False
        if self.max_market_cap is not None and constituent.market_cap > self.max_market_cap:
            return False

        # Volume filtering
        if self.min_average_daily_volume is not None:
            if constituent.average_daily_volume < self.min_average_daily_volume:
                return False

        # Free float filtering
        if self.min_free_float is not None:
            if constituent.free_float_factor < self.min_free_float:
                return False

        # ESG screening
        if self.esg_screening:
            if not self._passes_esg_screening(constituent):
                return False

        # Custom filters
        for custom_filter in self.custom_filters:
            if not custom_filter(constituent):
                return False

        return True

    def _passes_esg_screening(self, constituent: Constituent) -> bool:
        """Check if constituent passes ESG screening."""
        if self.esg_screening is None:
            return True

        esg = self.esg_screening

        if esg.min_esg_score is not None:
            if constituent.esg_score is None or constituent.esg_score < esg.min_esg_score:
                return False

        if esg.min_environmental_score is not None:
            if (
                constituent.environmental_score is None
                or constituent.environmental_score < esg.min_environmental_score
            ):
                return False

        if esg.min_social_score is not None:
            if constituent.social_score is None or constituent.social_score < esg.min_social_score:
                return False

        if esg.min_governance_score is not None:
            if (
                constituent.governance_score is None
                or constituent.governance_score < esg.min_governance_score
            ):
                return False

        # Exclusion screening would require additional sector/industry data
        # This is a simplified implementation

        return True

    def filter(self, constituents: list[Constituent]) -> list[Constituent]:
        """
        Filter a list of constituents by universe criteria.

        Args:
            constituents: List of constituents to filter

        Returns:
            List of eligible constituents
        """
        return [c for c in constituents if self.is_eligible(c)]

    def to_dict(self) -> dict:
        """Convert universe to dictionary."""
        return {
            "asset_class": str(self.asset_class),
            "regions": [str(r) for r in self.regions],
            "countries": self.countries,
            "exclude_countries": self.exclude_countries,
            "sectors": self.sectors,
            "exclude_sectors": self.exclude_sectors,
            "tickers": self.tickers,
            "min_market_cap": self.min_market_cap,
            "max_market_cap": self.max_market_cap,
            "min_average_daily_volume": self.min_average_daily_volume,
            "min_free_float": self.min_free_float,
            "currency": str(self.currency),
        }


class UniverseBuilder:
    """
    Builder for constructing Universe objects with fluent syntax.

    Example:
        >>> universe = (Universe.builder()
        ...     .asset_class(AssetClass.EQUITIES)
        ...     .regions([Region.NORTH_AMERICA, Region.EUROPE])
        ...     .sectors(["Technology", "Healthcare"])
        ...     .min_market_cap(1_000_000_000)
        ...     .min_free_float(0.15)
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        self._asset_class: AssetClass = AssetClass.EQUITIES
        self._regions: list[Region] = []
        self._countries: list[str] = []
        self._exclude_countries: list[str] = []
        self._sectors: list[str] = []
        self._exclude_sectors: list[str] = []
        self._industries: list[str] = []
        self._exchanges: list[str] = []
        self._tickers: list[str] = []
        self._min_market_cap: Optional[float] = None
        self._max_market_cap: Optional[float] = None
        self._min_average_daily_volume: Optional[float] = None
        self._min_free_float: Optional[float] = None
        self._currency: Currency = Currency.USD
        self._esg_screening: Optional[ESGScreening] = None
        self._custom_filters: list[Callable[[Constituent], bool]] = []

    def asset_class(self, asset_class: AssetClass) -> "UniverseBuilder":
        """Set the asset class."""
        self._asset_class = asset_class
        return self

    def regions(self, regions: list[Region]) -> "UniverseBuilder":
        """Set the geographic regions."""
        self._regions = regions
        return self

    def countries(self, countries: list[Union[Country, Region, str]]) -> "UniverseBuilder":
        """
        Set specific countries to include.

        Args:
            countries: ISO country codes or Region enums
        """
        self._countries = [str(c) for c in countries]
        return self

    def exclude_countries(self, countries: list[Union[Country, Region, str]]) -> "UniverseBuilder":
        """
        Set countries to exclude.

        Args:
            countries: ISO country codes or Region enums
        """
        self._exclude_countries = [str(c) for c in countries]
        return self

    def sectors(self, sectors: list[Union[Sector, str]]) -> "UniverseBuilder":
        """
        Set industry sectors to include.

        Args:
            sectors: List of Sector enums or strings

        Example:
            >>> universe = (Universe.builder()
            ...     .sectors([Sector.TECHNOLOGY, Sector.HEALTH_CARE])
            ...     .build()
            ... )
        """
        self._sectors = [str(s) if isinstance(s, Sector) else s for s in sectors]
        return self

    def exclude_sectors(self, sectors: list[Union[Sector, str]]) -> "UniverseBuilder":
        """
        Set sectors to exclude.

        Args:
            sectors: List of Sector enums or strings

        Example:
            >>> universe = (Universe.builder()
            ...     .exclude_sectors([Sector.ENERGY, Sector.UTILITIES])
            ...     .build()
            ... )
        """
        self._exclude_sectors = [str(s) if isinstance(s, Sector) else s for s in sectors]
        return self

    def industries(self, industries: list[str]) -> "UniverseBuilder":
        """Set industries to include."""
        self._industries = industries
        return self

    def exchanges(self, exchanges: list[str]) -> "UniverseBuilder":
        """Set exchanges to include."""
        self._exchanges = exchanges
        return self

    def tickers(self, tickers: list[str]) -> "UniverseBuilder":
        """Set specific tickers (for static universe)."""
        self._tickers = tickers
        return self

    def min_market_cap(
        self, amount: float, currency: Optional[Currency] = None
    ) -> "UniverseBuilder":
        """Set minimum market capitalization."""
        self._min_market_cap = amount
        if currency:
            self._currency = currency
        return self

    def max_market_cap(self, amount: float) -> "UniverseBuilder":
        """Set maximum market capitalization."""
        self._max_market_cap = amount
        return self

    def min_average_daily_volume(
        self, volume: float, currency: Optional[Currency] = None
    ) -> "UniverseBuilder":
        """Set minimum average daily trading volume."""
        self._min_average_daily_volume = volume
        if currency:
            self._currency = currency
        return self

    def min_free_float(self, ratio: float) -> "UniverseBuilder":
        """Set minimum free-float ratio (0.0 to 1.0)."""
        if not 0.0 <= ratio <= 1.0:
            raise ValueError("Free float ratio must be between 0.0 and 1.0")
        self._min_free_float = ratio
        return self

    def currency(self, currency: Currency) -> "UniverseBuilder":
        """Set the currency for market cap and volume thresholds."""
        self._currency = currency
        return self

    def esg_screening(
        self,
        min_esg_score: Optional[float] = None,
        exclude_controversial_weapons: bool = False,
        exclude_tobacco: bool = False,
        exclude_thermal_coal: bool = False,
        **kwargs,
    ) -> "UniverseBuilder":
        """Set ESG screening criteria."""
        self._esg_screening = ESGScreening(
            min_esg_score=min_esg_score,
            exclude_controversial_weapons=exclude_controversial_weapons,
            exclude_tobacco=exclude_tobacco,
            exclude_thermal_coal=exclude_thermal_coal,
            **kwargs,
        )
        return self

    def custom_filter(self, filter_fn: Callable[[Constituent], bool]) -> "UniverseBuilder":
        """Add a custom filter function."""
        self._custom_filters.append(filter_fn)
        return self

    def build(self) -> Universe:
        """Build the Universe object."""
        return Universe(
            asset_class=self._asset_class,
            regions=self._regions,
            countries=self._countries,
            exclude_countries=self._exclude_countries,
            sectors=self._sectors,
            exclude_sectors=self._exclude_sectors,
            industries=self._industries,
            exchanges=self._exchanges,
            tickers=self._tickers,
            min_market_cap=self._min_market_cap,
            max_market_cap=self._max_market_cap,
            min_average_daily_volume=self._min_average_daily_volume,
            min_free_float=self._min_free_float,
            currency=self._currency,
            esg_screening=self._esg_screening,
            custom_filters=self._custom_filters,
        )
