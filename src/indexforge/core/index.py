"""
Main Index class - the primary entry point for index creation.

The Index class represents a financial index and orchestrates
all components (universe, selection, weighting, data, calculation).
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd

from indexforge.core.constituent import Constituent
from indexforge.core.types import Currency, IndexType
from indexforge.core.universe import Universe
from indexforge.data.provider import DataProvider
from indexforge.rebalancing.schedule import RebalancingSchedule
from indexforge.selection.criteria import SelectionCriteria
from indexforge.validation.report import ValidationReport
from indexforge.validation.rules import ValidationRules
from indexforge.weighting.methods import WeightingMethod

logger = logging.getLogger(__name__)


@dataclass
class Performance:
    """Performance metrics for an index."""

    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    start_date: str
    end_date: str

    def __str__(self) -> str:
        return (
            f"Performance ({self.start_date} to {self.end_date}):\n"
            f"  Total Return: {self.total_return:.2%}\n"
            f"  Annualized Return: {self.annualized_return:.2%}\n"
            f"  Volatility: {self.volatility:.2%}\n"
            f"  Sharpe Ratio: {self.sharpe_ratio:.2f}\n"
            f"  Max Drawdown: {self.max_drawdown:.2%}"
        )


@dataclass
class BacktestResult:
    """Results from backtesting an index."""

    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    index_series: pd.Series
    start_date: str
    end_date: str

    def __str__(self) -> str:
        return (
            f"Backtest Results ({self.start_date} to {self.end_date}):\n"
            f"  Annualized Return: {self.annualized_return:.2%}\n"
            f"  Volatility: {self.volatility:.2%}\n"
            f"  Sharpe Ratio: {self.sharpe_ratio:.2f}\n"
            f"  Max Drawdown: {self.max_drawdown:.2%}\n"
            f"  Total Return: {self.total_return:.2%}"
        )


class Index:
    """
    Represents a financial index.

    The Index class is the main entry point for creating and managing
    indices. It brings together all components:
    - Universe: What can be in the index
    - Selection: How constituents are chosen
    - Weighting: How constituents are weighted
    - Rebalancing: When the index is updated
    - Data: Where market data comes from

    Example:
        >>> from indexforge import Index, Universe, WeightingMethod, Currency
        >>>
        >>> # Create an index
        >>> index = Index.create(
        ...     name="Tech Leaders Index",
        ...     identifier="TECHLDRS",
        ...     currency=Currency.USD,
        ...     base_date="2025-01-01",
        ...     base_value=1000.0
        ... )
        >>>
        >>> # Configure it
        >>> index.set_universe(Universe.from_tickers(["AAPL", "MSFT", "GOOGL"]))
        >>> index.set_weighting_method(WeightingMethod.equal_weight())
        >>>
        >>> # Calculate
        >>> value = index.calculate(date="2025-11-15")
        >>> print(f"Index value: {value}")
    """

    def __init__(
        self,
        name: str,
        identifier: str,
        currency: Currency,
        base_date: str,
        base_value: float,
        index_type: IndexType = IndexType.PRICE_RETURN,
        isin: Optional[str] = None,
    ) -> None:
        """
        Initialize an Index.

        Use Index.create() factory method instead of calling directly.
        """
        self._name = name
        self._identifier = identifier
        self._currency = currency
        self._base_date = base_date
        self._base_value = base_value
        self._index_type = index_type
        self._isin = isin

        # Components (set via setter methods)
        self._universe: Optional[Universe] = None
        self._selection_criteria: Optional[SelectionCriteria] = None
        self._weighting_method: WeightingMethod = WeightingMethod.equal_weight()
        self._rebalancing_schedule: RebalancingSchedule = RebalancingSchedule.quarterly()
        self._data_provider: DataProvider = DataProvider.default()
        self._validation_rules: ValidationRules = ValidationRules.default()

        # State
        self._constituents: list[Constituent] = []
        self._divisor: float = 1.0
        self._last_calculation_date: Optional[str] = None

    @staticmethod
    def create(
        name: str,
        identifier: str,
        currency: Union[Currency, str],
        base_date: str,
        base_value: float,
        index_type: Union[IndexType, str] = IndexType.PRICE_RETURN,
        isin: Optional[str] = None,
    ) -> "Index":
        """
        Create a new Index.

        Args:
            name: Full name of the index
            identifier: Short identifier/ticker
            currency: Calculation currency
            base_date: Index inception date (YYYY-MM-DD)
            base_value: Starting index value
            index_type: Type of return calculation
            isin: ISIN code (optional)

        Returns:
            New Index instance

        Example:
            >>> index = Index.create(
            ...     name="Tech Leaders Index",
            ...     identifier="TECHLDRS",
            ...     currency=Currency.USD,
            ...     base_date="2025-01-01",
            ...     base_value=1000.0
            ... )
        """
        # Convert string to enum if needed
        if isinstance(currency, str):
            currency = Currency(currency)
        if isinstance(index_type, str):
            index_type = IndexType(index_type)

        return Index(
            name=name,
            identifier=identifier,
            currency=currency,
            base_date=base_date,
            base_value=base_value,
            index_type=index_type,
            isin=isin,
        )

    # ==================== Configuration Methods ====================

    def set_universe(self, universe: Universe) -> "Index":
        """
        Set the investment universe.

        Args:
            universe: Universe defining eligible securities

        Returns:
            Self for method chaining
        """
        self._universe = universe
        return self

    def set_selection_criteria(self, criteria: SelectionCriteria) -> "Index":
        """
        Set the selection criteria.

        Args:
            criteria: Criteria for selecting constituents

        Returns:
            Self for method chaining
        """
        self._selection_criteria = criteria
        return self

    def set_weighting_method(self, method: WeightingMethod) -> "Index":
        """
        Set the weighting method.

        Args:
            method: Method for weighting constituents

        Returns:
            Self for method chaining
        """
        self._weighting_method = method
        return self

    def set_rebalancing_schedule(self, schedule: RebalancingSchedule) -> "Index":
        """
        Set the rebalancing schedule.

        Args:
            schedule: Schedule for index rebalancing

        Returns:
            Self for method chaining
        """
        self._rebalancing_schedule = schedule
        return self

    def set_data_provider(self, provider: DataProvider) -> "Index":
        """
        Set the data provider.

        Args:
            provider: Data provider for market data

        Returns:
            Self for method chaining
        """
        self._data_provider = provider
        return self

    def set_validation_rules(self, rules: ValidationRules) -> "Index":
        """
        Set validation rules.

        Args:
            rules: Rules for validating index composition

        Returns:
            Self for method chaining
        """
        self._validation_rules = rules
        return self

    # ==================== Calculation Methods ====================

    def calculate(self, date: str) -> float:
        """
        Calculate the index value for a given date.

        Args:
            date: Calculation date (YYYY-MM-DD)

        Returns:
            Index value

        Example:
            >>> value = index.calculate(date="2025-11-15")
            >>> print(f"Index value: {value:.2f}")
        """
        if not self._universe:
            raise ValueError("Universe must be set before calculation")

        # Get/update constituents
        self._update_constituents(date)

        if not self._constituents:
            logger.warning("No constituents found, returning base value")
            return self._base_value

        # Calculate index value based on weighted prices
        index_value = 0.0
        for constituent in self._constituents:
            index_value += constituent.price * constituent.weight

        # Apply divisor and normalize to base value
        if self._divisor > 0:
            index_value = (index_value / self._divisor) * self._base_value

        self._last_calculation_date = date
        return index_value

    def _update_constituents(self, as_of_date: str) -> None:
        """Update constituents with current data."""
        if not self._universe:
            return

        # Get tickers from universe
        tickers = self._universe.tickers if self._universe.tickers else []

        if not tickers:
            logger.warning("No tickers in universe")
            return

        # Fetch constituent data
        constituents = self._data_provider.get_constituent_data(tickers, as_of_date)

        # Filter by universe criteria
        eligible = self._universe.filter(constituents)

        # Apply selection criteria if set
        if self._selection_criteria:
            selected = self._selection_criteria.select(
                eligible, self._constituents  # Pass current for buffer rules
            )
        else:
            selected = eligible

        # Calculate weights
        weights = self._weighting_method.calculate_weights(selected)

        # Update constituent weights
        for constituent in selected:
            constituent.weight = weights.get(constituent.ticker, 0.0)

        # Update divisor on first calculation
        if not self._constituents:
            total_price_weight = sum(c.price * c.weight for c in selected if c.price)
            if total_price_weight > 0:
                self._divisor = total_price_weight / self._base_value

        self._constituents = selected

    def get_constituents(self, date: Optional[str] = None) -> list[Constituent]:
        """
        Get current index constituents.

        Args:
            date: Optional date for constituent data

        Returns:
            List of Constituent objects

        Example:
            >>> constituents = index.get_constituents()
            >>> for c in constituents:
            ...     print(f"{c.ticker}: {c.weight:.2%}")
        """
        if date and date != self._last_calculation_date:
            self._update_constituents(date)
        return self._constituents

    def get_performance(self, start_date: str, end_date: str) -> Performance:
        """
        Calculate performance metrics for a period.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Performance object with metrics
        """
        backtest = self.backtest(start_date, end_date, self._base_value)

        return Performance(
            total_return=backtest.total_return,
            annualized_return=backtest.annualized_return,
            volatility=backtest.volatility,
            sharpe_ratio=backtest.sharpe_ratio,
            max_drawdown=backtest.max_drawdown,
            start_date=start_date,
            end_date=end_date,
        )

    def get_timeseries(
        self, start_date: str, end_date: str, frequency: str = "daily"
    ) -> pd.DataFrame:
        """
        Get index time series data.

        Args:
            start_date: Start date
            end_date: End date
            frequency: Data frequency (daily, weekly, monthly)

        Returns:
            DataFrame with index values
        """
        backtest = self.backtest(start_date, end_date, self._base_value)

        df = pd.DataFrame(
            {"date": backtest.index_series.index, "value": backtest.index_series.values}
        )
        df.set_index("date", inplace=True)

        # Resample if needed
        if frequency == "weekly":
            df = df.resample("W").last()
        elif frequency == "monthly":
            df = df.resample("M").last()

        return df

    # ==================== Backtesting ====================

    def backtest(
        self, start_date: str, end_date: str, initial_value: float = 1000.0
    ) -> BacktestResult:
        """
        Backtest the index over a historical period.

        Args:
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            initial_value: Starting index value

        Returns:
            BacktestResult with performance metrics

        Example:
            >>> result = index.backtest(
            ...     start_date="2020-01-01",
            ...     end_date="2024-12-31",
            ...     initial_value=1000.0
            ... )
            >>> print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        """
        if not self._universe:
            raise ValueError("Universe must be set before backtesting")

        tickers = self._universe.tickers if self._universe.tickers else []
        if not tickers:
            raise ValueError("No tickers in universe")

        # Fetch price data
        prices = self._data_provider.get_prices(tickers, start_date, end_date)

        if prices.empty:
            raise ValueError("No price data available for the period")

        # Get closing prices
        if isinstance(prices.columns, pd.MultiIndex):
            # Multi-ticker format
            close_prices = prices.xs("Close", axis=1, level=1)
        else:
            # Single ticker
            close_prices = prices[["Close"]]
            close_prices.columns = tickers

        # Fill missing values
        close_prices = close_prices.ffill().dropna()

        if close_prices.empty:
            raise ValueError("No valid price data after cleaning")

        # Get constituent data for weighting
        constituents = self._data_provider.get_constituent_data(tickers)
        constituent_lookup = {c.ticker: c for c in constituents}

        # Calculate weights (simplified - using start weights throughout)
        available_tickers = [t for t in tickers if t in close_prices.columns]
        available_constituents = [
            constituent_lookup.get(t) or Constituent(ticker=t) for t in available_tickers
        ]

        weights_dict = self._weighting_method.calculate_weights(available_constituents)
        weights = pd.Series({t: weights_dict.get(t, 0) for t in available_tickers})

        # Normalize weights for available tickers
        weights = weights / weights.sum()

        # Calculate returns
        returns = close_prices[available_tickers].pct_change().dropna()

        # Weighted returns
        weighted_returns = (returns * weights).sum(axis=1)

        # Index series
        index_series = (1 + weighted_returns).cumprod() * initial_value

        # Calculate metrics
        total_return = (index_series.iloc[-1] / initial_value) - 1

        # Annualized return
        trading_days = len(returns)
        years = trading_days / 252
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Volatility (annualized)
        volatility = weighted_returns.std() * np.sqrt(252)

        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0

        # Max drawdown
        rolling_max = index_series.expanding().max()
        drawdown = (index_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        return BacktestResult(
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_return=total_return,
            index_series=index_series,
            start_date=start_date,
            end_date=end_date,
        )

    # ==================== Validation ====================

    def validate(self) -> ValidationReport:
        """
        Validate the index configuration and composition.

        Returns:
            ValidationReport with any issues found

        Example:
            >>> report = index.validate()
            >>> if not report.is_valid:
            ...     print(report)
        """
        report = ValidationReport()

        # Check required components
        if not self._universe:
            report.add_error(
                field="universe",
                message="Universe is not set",
                suggestion="Call set_universe() with a Universe object",
            )

        if not self._name:
            report.add_error(field="name", message="Index name is not set")

        if not self._identifier:
            report.add_error(field="identifier", message="Index identifier is not set")

        # Validate constituents if available
        if self._constituents:
            constituent_report = self._validation_rules.validate_constituents(self._constituents)
            report.merge(constituent_report)

        return report

    # ==================== Serialization ====================

    def save(self, path: str) -> None:
        """
        Save index configuration to file.

        Args:
            path: Path to save file (JSON)

        Example:
            >>> index.save("my_index.json")
        """
        config = self.to_dict()

        with open(path, "w") as f:
            json.dump(config, f, indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> "Index":
        """
        Load index configuration from file.

        Args:
            path: Path to configuration file

        Returns:
            Index instance

        Example:
            >>> index = Index.load("my_index.json")
        """
        with open(path) as f:
            config = json.load(f)

        return cls.from_dict(config)

    def to_dict(self) -> dict:
        """Convert index configuration to dictionary."""
        return {
            "name": self._name,
            "identifier": self._identifier,
            "currency": str(self._currency),
            "base_date": self._base_date,
            "base_value": self._base_value,
            "index_type": str(self._index_type),
            "isin": self._isin,
            "universe": self._universe.to_dict() if self._universe else None,
            "selection_criteria": (
                self._selection_criteria.to_dict() if self._selection_criteria else None
            ),
            "weighting_method": (
                self._weighting_method.to_dict() if self._weighting_method else None
            ),
            "rebalancing_schedule": (
                self._rebalancing_schedule.to_dict() if self._rebalancing_schedule else None
            ),
            "validation_rules": (
                self._validation_rules.to_dict() if self._validation_rules else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Index":
        """Create index from dictionary."""
        index = cls.create(
            name=data["name"],
            identifier=data["identifier"],
            currency=Currency(data["currency"]),
            base_date=data["base_date"],
            base_value=data["base_value"],
            index_type=IndexType(data.get("index_type", "PRICE_RETURN")),
            isin=data.get("isin"),
        )

        # Restore universe from tickers if available
        if data.get("universe") and data["universe"].get("tickers"):
            index.set_universe(Universe.from_tickers(data["universe"]["tickers"]))

        return index

    # ==================== Properties ====================

    # ==================== Properties ====================
    # Direct access to index attributes - preferred over to_dict()

    @property
    def name(self) -> str:
        """Get index name."""
        return self._name

    @property
    def identifier(self) -> str:
        """Get index identifier."""
        return self._identifier

    @property
    def isin(self) -> Optional[str]:
        """Get ISIN code."""
        return self._isin

    @property
    def currency(self) -> Currency:
        """Get calculation currency."""
        return self._currency

    @property
    def base_date(self) -> str:
        """Get base date."""
        return self._base_date

    @property
    def base_value(self) -> float:
        """Get base value."""
        return self._base_value

    @property
    def index_type(self) -> IndexType:
        """Get index type."""
        return self._index_type

    @property
    def universe(self) -> Optional[Universe]:
        """Get the investment universe."""
        return self._universe

    @property
    def selection_criteria(self) -> Optional[SelectionCriteria]:
        """Get the selection criteria."""
        return self._selection_criteria

    @property
    def weighting_method(self) -> WeightingMethod:
        """Get the weighting method."""
        return self._weighting_method

    @property
    def rebalancing_schedule(self) -> RebalancingSchedule:
        """Get the rebalancing schedule."""
        return self._rebalancing_schedule

    @property
    def validation_rules(self) -> ValidationRules:
        """Get the validation rules."""
        return self._validation_rules

    @property
    def constituents(self) -> list[Constituent]:
        """Get current constituents."""
        return self._constituents

    def __repr__(self) -> str:
        return f"Index(name='{self._name}', identifier='{self._identifier}')"

    def __str__(self) -> str:
        return f"{self._name} ({self._identifier})"
