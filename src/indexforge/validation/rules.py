"""
Validation rules for index configuration and compliance.
"""

from dataclasses import dataclass
from typing import Optional

from indexforge.core.constituent import Constituent
from indexforge.validation.report import ValidationReport


@dataclass
class ValidationRules:
    """
    Rules for validating index configuration and composition.

    Attributes:
        min_constituents: Minimum number of constituents
        max_constituents: Maximum number of constituents
        max_single_constituent_weight: Maximum weight for a single constituent
        max_single_sector_weight: Maximum weight for a single sector
        max_single_country_weight: Maximum weight for a single country
        min_market_cap: Minimum total index market cap
        require_minimum_turnover: Flag turnover below this threshold

    Example:
        >>> rules = (ValidationRules.builder()
        ...     .min_constituents(30)
        ...     .max_constituents(50)
        ...     .max_single_constituent_weight(0.10)
        ...     .build()
        ... )
    """

    min_constituents: Optional[int] = None
    max_constituents: Optional[int] = None
    max_single_constituent_weight: Optional[float] = None
    max_single_sector_weight: Optional[float] = None
    max_single_country_weight: Optional[float] = None
    min_market_cap: Optional[float] = None
    require_minimum_turnover: Optional[float] = None

    @staticmethod
    def builder() -> "ValidationRulesBuilder":
        """Create a new ValidationRulesBuilder."""
        return ValidationRulesBuilder()

    @staticmethod
    def default() -> "ValidationRules":
        """Create default validation rules."""
        return ValidationRules(
            min_constituents=1,
            max_single_constituent_weight=1.0,
        )

    def validate_constituents(self, constituents: list[Constituent]) -> ValidationReport:
        """
        Validate index constituents against the rules.

        Args:
            constituents: List of constituents to validate

        Returns:
            ValidationReport with any issues found
        """
        report = ValidationReport()

        # Check constituent count
        count = len(constituents)
        if self.min_constituents and count < self.min_constituents:
            report.add_error(
                field="constituent_count",
                message="Too few constituents",
                current_value=count,
                expected=f"At least {self.min_constituents}",
                suggestion="Add more constituents or adjust selection criteria",
            )

        if self.max_constituents and count > self.max_constituents:
            report.add_error(
                field="constituent_count",
                message="Too many constituents",
                current_value=count,
                expected=f"At most {self.max_constituents}",
                suggestion="Reduce select_top parameter in selection criteria",
            )

        # Check individual weights
        if self.max_single_constituent_weight:
            for c in constituents:
                if c.weight > self.max_single_constituent_weight:
                    report.add_error(
                        field=f"weight.{c.ticker}",
                        message="Constituent weight exceeds maximum",
                        current_value=f"{c.weight:.2%}",
                        expected=f"At most {self.max_single_constituent_weight:.2%}",
                        suggestion="Apply weight cap in weighting method",
                    )

        # Check sector concentration
        if self.max_single_sector_weight:
            sector_weights: dict[str, float] = {}
            for c in constituents:
                sector_weights[c.sector] = sector_weights.get(c.sector, 0) + c.weight

            for sector, weight in sector_weights.items():
                if weight > self.max_single_sector_weight:
                    report.add_error(
                        field=f"sector_weight.{sector}",
                        message="Sector weight exceeds maximum",
                        current_value=f"{weight:.2%}",
                        expected=f"At most {self.max_single_sector_weight:.2%}",
                        suggestion="Apply sector cap in weighting method",
                    )

        # Check country concentration
        if self.max_single_country_weight:
            country_weights: dict[str, float] = {}
            for c in constituents:
                country_weights[c.country] = country_weights.get(c.country, 0) + c.weight

            for country, weight in country_weights.items():
                if weight > self.max_single_country_weight:
                    report.add_error(
                        field=f"country_weight.{country}",
                        message="Country weight exceeds maximum",
                        current_value=f"{weight:.2%}",
                        expected=f"At most {self.max_single_country_weight:.2%}",
                        suggestion="Apply country cap in weighting method",
                    )

        # Check total market cap
        if self.min_market_cap:
            total_cap = sum(c.market_cap for c in constituents)
            if total_cap < self.min_market_cap:
                report.add_warning(
                    field="total_market_cap",
                    message="Total market cap below minimum",
                    current_value=f"${total_cap:,.0f}",
                    expected=f"At least ${self.min_market_cap:,.0f}",
                )

        # Validate weights sum to approximately 1
        total_weight = sum(c.weight for c in constituents)
        if abs(total_weight - 1.0) > 0.01:
            report.add_warning(
                field="total_weight",
                message="Weights do not sum to 1.0",
                current_value=f"{total_weight:.4f}",
                expected="1.0000",
                suggestion="Ensure weighting method normalizes weights",
            )

        return report

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "min_constituents": self.min_constituents,
            "max_constituents": self.max_constituents,
            "max_single_constituent_weight": self.max_single_constituent_weight,
            "max_single_sector_weight": self.max_single_sector_weight,
            "max_single_country_weight": self.max_single_country_weight,
            "min_market_cap": self.min_market_cap,
        }


class ValidationRulesBuilder:
    """
    Builder for constructing ValidationRules with fluent syntax.

    Example:
        >>> rules = (ValidationRules.builder()
        ...     .min_constituents(20)
        ...     .max_constituents(100)
        ...     .max_single_constituent_weight(0.15)
        ...     .max_single_country_weight(0.50)
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        self._min_constituents: Optional[int] = None
        self._max_constituents: Optional[int] = None
        self._max_single_constituent_weight: Optional[float] = None
        self._max_single_sector_weight: Optional[float] = None
        self._max_single_country_weight: Optional[float] = None
        self._min_market_cap: Optional[float] = None
        self._require_minimum_turnover: Optional[float] = None

    def min_constituents(self, count: int) -> "ValidationRulesBuilder":
        """Set minimum constituent count."""
        if count < 1:
            raise ValueError("Minimum constituents must be at least 1")
        self._min_constituents = count
        return self

    def max_constituents(self, count: int) -> "ValidationRulesBuilder":
        """Set maximum constituent count."""
        if count < 1:
            raise ValueError("Maximum constituents must be at least 1")
        self._max_constituents = count
        return self

    def max_single_constituent_weight(self, weight: float) -> "ValidationRulesBuilder":
        """Set maximum weight for a single constituent (0.0 to 1.0)."""
        if not 0.0 < weight <= 1.0:
            raise ValueError("Weight must be between 0 and 1")
        self._max_single_constituent_weight = weight
        return self

    def max_single_sector_weight(self, weight: float) -> "ValidationRulesBuilder":
        """Set maximum weight for a single sector (0.0 to 1.0)."""
        if not 0.0 < weight <= 1.0:
            raise ValueError("Weight must be between 0 and 1")
        self._max_single_sector_weight = weight
        return self

    def max_single_country_weight(self, weight: float) -> "ValidationRulesBuilder":
        """Set maximum weight for a single country (0.0 to 1.0)."""
        if not 0.0 < weight <= 1.0:
            raise ValueError("Weight must be between 0 and 1")
        self._max_single_country_weight = weight
        return self

    def min_market_cap(self, amount: float) -> "ValidationRulesBuilder":
        """Set minimum total market cap."""
        self._min_market_cap = amount
        return self

    def require_minimum_turnover(self, ratio: float) -> "ValidationRulesBuilder":
        """Flag if turnover is below this threshold."""
        if not 0.0 <= ratio <= 1.0:
            raise ValueError("Turnover ratio must be between 0 and 1")
        self._require_minimum_turnover = ratio
        return self

    def build(self) -> ValidationRules:
        """Build the ValidationRules object."""
        return ValidationRules(
            min_constituents=self._min_constituents,
            max_constituents=self._max_constituents,
            max_single_constituent_weight=self._max_single_constituent_weight,
            max_single_sector_weight=self._max_single_sector_weight,
            max_single_country_weight=self._max_single_country_weight,
            min_market_cap=self._min_market_cap,
            require_minimum_turnover=self._require_minimum_turnover,
        )
