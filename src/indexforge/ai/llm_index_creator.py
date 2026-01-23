"""
LLM-powered index creation.

Uses large language models to interpret natural language descriptions
and create financial indices using the indexforge API.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional, Union, cast

from indexforge.core.index import Index
from indexforge.core.types import Currency, Factor, IndexType, Region, Sector
from indexforge.core.universe import Universe
from indexforge.rebalancing.schedule import RebalancingSchedule
from indexforge.selection.criteria import SelectionCriteria
from indexforge.weighting.methods import WeightingMethod

logger = logging.getLogger(__name__)


# System prompt that teaches the LLM about indexforge's API
SYSTEM_PROMPT = """You are an expert financial index designer. Your task is to interpret natural language descriptions of financial indices and convert them into structured JSON configurations.

## Available Index Configuration Options

### Basic Index Properties
- name: Full name of the index (e.g., "US Large Cap Technology Index")
- identifier: Short ticker-like identifier (e.g., "USLCTECH")
- currency: USD, EUR, GBP, JPY, CHF, etc.
- base_date: Index inception date (YYYY-MM-DD format)
- base_value: Starting index value (typically 100 or 1000)
- index_type: PRICE_RETURN (default), TOTAL_RETURN, or NET_TOTAL_RETURN

### Universe (What securities are eligible)
- tickers: List of specific ticker symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
- regions: NORTH_AMERICA, EUROPE, ASIA_PACIFIC, EMERGING_MARKETS, GLOBAL
- sectors: TECHNOLOGY, HEALTH_CARE, FINANCIALS, CONSUMER_DISCRETIONARY, CONSUMER_STAPLES, INDUSTRIALS, ENERGY, MATERIALS, UTILITIES, REAL_ESTATE, COMMUNICATION_SERVICES
- countries: List of ISO country codes (e.g., ["US", "CA", "MX"])
- exclude_countries: Countries to exclude
- exclude_sectors: Sectors to exclude
- min_market_cap: Minimum market cap in billions (e.g., 10 for $10B+)
- max_market_cap: Maximum market cap in billions
- min_free_float: Minimum free-float ratio (0.0 to 1.0)

### Selection Criteria (How to choose constituents)
- ranking_factor: MARKET_CAP, FREE_FLOAT_MARKET_CAP, LIQUIDITY, VOLUME, DIVIDEND_YIELD
- select_count: Number of constituents (e.g., 50, 100, 500)
- buffer_rules:
  - add_threshold: Rank required to be added (e.g., 45 means must rank in top 45)
  - remove_threshold: Rank at which removed (e.g., 60 means drops out if rank > 60)

### Weighting Method (How to weight constituents)
- scheme: EQUAL_WEIGHT, MARKET_CAP, FREE_FLOAT_MARKET_CAP, FACTOR_BASED
- factor: For factor-based weighting (MARKET_CAP, LIQUIDITY, DIVIDEND_YIELD, etc.)
- caps:
  - max_weight: Maximum weight per constituent (e.g., 0.10 for 10%)
  - max_weight_per_sector: Maximum weight per sector (e.g., 0.30 for 30%)
  - max_weight_per_country: Maximum weight per country

### Rebalancing Schedule
- frequency: DAILY, WEEKLY, MONTHLY, QUARTERLY, SEMI_ANNUAL, ANNUAL
- months: List of months for rebalancing (e.g., [3, 6, 9, 12] for quarterly)
- day: Day of month (e.g., 15 for mid-month)

## Common Index Types and Examples

1. **Market Cap Weighted Index**: Weight by market cap, often with caps
2. **Equal Weight Index**: All constituents get equal weight
3. **Factor Index**: Weight by a specific factor (dividend yield, momentum, etc.)
4. **Thematic Index**: Focus on specific themes (AI, clean energy, etc.)
5. **ESG Index**: With ESG screening criteria

## Output Format

Return a JSON object with this structure:
```json
{
  "name": "Index Name",
  "identifier": "TICKER",
  "currency": "USD",
  "base_date": "2024-01-01",
  "base_value": 1000,
  "index_type": "PRICE_RETURN",
  "universe": {
    "tickers": [],
    "regions": [],
    "sectors": [],
    "countries": [],
    "exclude_sectors": [],
    "min_market_cap": null,
    "min_free_float": null
  },
  "selection": {
    "ranking_factor": "MARKET_CAP",
    "select_count": 50,
    "buffer_rules": null
  },
  "weighting": {
    "scheme": "MARKET_CAP",
    "factor": null,
    "caps": {
      "max_weight": null,
      "max_weight_per_sector": null
    }
  },
  "rebalancing": {
    "frequency": "QUARTERLY",
    "months": [3, 6, 9, 12],
    "day": 15
  },
  "explanation": "Brief explanation of the index design choices"
}
```

## Important Guidelines

1. If specific tickers are mentioned, include them in the universe
2. If no tickers are specified but criteria are given, leave tickers empty and set appropriate filters
3. For US-only indices, set countries to ["US"]
4. Default to MARKET_CAP weighting if not specified
5. Default to QUARTERLY rebalancing if not specified
6. Use reasonable defaults: base_value=1000, base_date=today
7. Be conservative with caps - suggest 10% single stock cap for diversification
8. Include an explanation of your design choices

ONLY respond with valid JSON. Do not include any other text."""


@dataclass
class IndexAIConfig:
    """Configuration for the IndexAI class."""

    api_key: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 2000
    base_url: Optional[str] = None  # For custom API endpoints


@dataclass
class IndexCreationResult:
    """Result from AI-powered index creation."""

    index: Index
    config: dict[str, Any]
    explanation: str
    raw_response: str


class IndexAI:
    """
    AI-powered index creation using large language models.

    Interprets natural language descriptions and creates financial indices
    using the indexforge API.

    Example:
        >>> from indexforge.ai import IndexAI
        >>>
        >>> # Using environment variable OPENAI_API_KEY
        >>> ai = IndexAI()
        >>>
        >>> # Or with explicit API key
        >>> ai = IndexAI(api_key="sk-...")
        >>>
        >>> # Create an index from description
        >>> result = ai.create_index(
        ...     "Create an equal-weight index of the top 20 US tech stocks"
        ... )
        >>> print(result.index)
        >>> print(result.explanation)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[IndexAIConfig] = None,
    ):
        """
        Initialize IndexAI.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            config: Full configuration object
        """
        self.config = config or IndexAIConfig()
        if api_key:
            self.config.api_key = api_key
        elif not self.config.api_key:
            self.config.api_key = os.environ.get("OPENAI_API_KEY")

        if not self.config.api_key:
            raise ValueError(
                "API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package is required for AI features. "
                    "Install with: pip install openai"
                )

            client_kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url

            self._client = OpenAI(**client_kwargs)

        return self._client

    def create_index(
        self,
        description: str,
        base_date: Optional[str] = None,
        base_value: float = 1000.0,
    ) -> IndexCreationResult:
        """
        Create an index from a natural language description.

        Args:
            description: Natural language description of the desired index
            base_date: Override base date (default: today)
            base_value: Override base value (default: 1000)

        Returns:
            IndexCreationResult containing the index and metadata

        Example:
            >>> result = ai.create_index(
            ...     "Create a dividend aristocrats index with the top 50 US stocks "
            ...     "that have increased dividends for 25+ years, weighted by "
            ...     "dividend yield with a 4% single stock cap"
            ... )
            >>> print(result.index.name)
            >>> print(result.explanation)
        """
        # Add context to the description
        context = f"""
User request: {description}

Additional context:
- Today's date: {date.today().isoformat()}
- Default base value: {base_value}
"""
        if base_date:
            context += f"- Requested base date: {base_date}\n"

        # Call the LLM
        raw_response = self._call_llm(context)

        # Parse the response
        config = self._parse_response(raw_response)

        # Apply overrides
        if base_date:
            config["base_date"] = base_date
        if base_value != 1000.0:
            config["base_value"] = base_value

        # Build the index
        index = self._build_index(config)

        explanation = config.get("explanation", "Index created based on the provided description.")

        return IndexCreationResult(
            index=index,
            config=config,
            explanation=explanation,
            raw_response=raw_response,
        )

    def suggest_improvements(self, description: str) -> str:
        """
        Get suggestions for improving an index design.

        Args:
            description: Current index description or configuration

        Returns:
            Suggestions for improvement
        """
        prompt = f"""
Analyze this index design and suggest improvements:

{description}

Consider:
1. Diversification (sector, country, single stock concentration)
2. Investability (liquidity, replication cost)
3. Methodology clarity
4. Risk management

Provide 3-5 specific, actionable suggestions.
"""
        return self._call_llm(prompt)

    def explain_index(self, index: Index) -> str:
        """
        Generate a plain-English explanation of an index.

        Args:
            index: The index to explain

        Returns:
            Human-readable explanation
        """
        config = index.to_dict()
        prompt = f"""
Explain this index configuration in plain English for a financial professional:

{json.dumps(config, indent=2)}

Include:
1. What the index measures/represents
2. How constituents are selected
3. How constituents are weighted
4. When the index rebalances
5. Any notable features or constraints
"""
        return self._call_llm(prompt)

    def _call_llm(self, user_message: str) -> str:
        """Call the LLM with the given message."""
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        return str(response.choices[0].message.content)

    def _parse_response(self, response: str) -> dict:
        """Parse the LLM response into a configuration dictionary."""
        # Try to extract JSON from the response
        try:
            # Try direct JSON parsing first
            return cast(dict[str, Any], json.loads(response))
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if json_match:
            try:
                return cast(dict[str, Any], json.loads(json_match.group(1)))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return cast(dict[str, Any], json.loads(json_match.group()))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse LLM response as JSON: {response[:200]}...")

    def _build_index(self, config: dict) -> Index:
        """Build an Index object from the configuration dictionary."""
        # Create base index
        index = Index.create(
            name=config.get("name", "AI-Generated Index"),
            identifier=config.get("identifier", "AIGEN"),
            currency=Currency(config.get("currency", "USD")),
            base_date=config.get("base_date", date.today().isoformat()),
            base_value=config.get("base_value", 1000.0),
            index_type=IndexType(config.get("index_type", "PRICE_RETURN")),
        )

        # Configure universe
        universe_config = config.get("universe", {})
        universe = self._build_universe(universe_config)
        if universe:
            index.set_universe(universe)

        # Configure selection criteria
        selection_config = config.get("selection", {})
        if selection_config:
            criteria = self._build_selection_criteria(selection_config)
            if criteria:
                index.set_selection_criteria(criteria)

        # Configure weighting method
        weighting_config = config.get("weighting", {})
        if weighting_config:
            method = self._build_weighting_method(weighting_config)
            if method:
                index.set_weighting_method(method)

        # Configure rebalancing schedule
        rebal_config = config.get("rebalancing", {})
        if rebal_config:
            schedule = self._build_rebalancing_schedule(rebal_config)
            if schedule:
                index.set_rebalancing_schedule(schedule)

        return index

    def _build_universe(self, config: dict) -> Optional[Universe]:
        """Build a Universe from configuration."""
        if not config:
            return None

        tickers = config.get("tickers", [])

        # If we have specific tickers, use them
        if tickers:
            return Universe.from_tickers(
                tickers=tickers,
                currency=Currency(config.get("currency", "USD")),
            )

        # Otherwise, build with filters
        builder = Universe.builder()

        # Regions
        regions = config.get("regions", [])
        if regions:
            region_enums = []
            for r in regions:
                try:
                    region_enums.append(Region(r))
                except ValueError:
                    logger.warning(f"Unknown region: {r}")
            if region_enums:
                builder.regions(region_enums)

        # Countries
        countries = config.get("countries", [])
        if countries:
            builder.countries(countries)

        exclude_countries = config.get("exclude_countries", [])
        if exclude_countries:
            builder.exclude_countries(exclude_countries)

        # Sectors
        sectors = config.get("sectors", [])
        if sectors:
            sector_list: list[Union[Sector, str]] = []
            for s in sectors:
                try:
                    sector_list.append(Sector(s))
                except ValueError:
                    sector_list.append(s)  # Use as string
            builder.sectors(sector_list)

        exclude_sectors = config.get("exclude_sectors", [])
        if exclude_sectors:
            builder.exclude_sectors(exclude_sectors)

        # Market cap filters
        min_cap = config.get("min_market_cap")
        if min_cap:
            # Convert billions to actual value
            builder.min_market_cap(min_cap * 1_000_000_000)

        max_cap = config.get("max_market_cap")
        if max_cap:
            builder.max_market_cap(max_cap * 1_000_000_000)

        # Free float
        min_ff = config.get("min_free_float")
        if min_ff:
            builder.min_free_float(min_ff)

        return builder.build()

    def _build_selection_criteria(self, config: dict) -> Optional[SelectionCriteria]:
        """Build SelectionCriteria from configuration."""
        if not config:
            return None

        builder = SelectionCriteria.builder()

        # Ranking factor
        ranking = config.get("ranking_factor")
        if ranking:
            try:
                builder.ranking_by(Factor(ranking))
            except ValueError:
                logger.warning(f"Unknown ranking factor: {ranking}")

        # Select count
        count = config.get("select_count")
        if count:
            builder.select_top(count)

        # Buffer rules
        buffer = config.get("buffer_rules")
        if buffer:
            builder.apply_buffer_rules(
                add_threshold=buffer.get("add_threshold"),
                remove_threshold=buffer.get("remove_threshold"),
            )

        return builder.build()

    def _build_weighting_method(self, config: dict) -> Optional[WeightingMethod]:
        """Build WeightingMethod from configuration."""
        if not config:
            return None

        scheme = config.get("scheme", "MARKET_CAP").upper()

        if scheme == "EQUAL_WEIGHT":
            return WeightingMethod.equal_weight()

        # For other schemes, use builder
        if scheme == "MARKET_CAP":
            builder = WeightingMethod.market_cap()
        elif scheme == "FREE_FLOAT_MARKET_CAP":
            builder = WeightingMethod.free_float_market_cap()
        elif scheme == "FACTOR_BASED":
            factor = config.get("factor")
            if factor:
                try:
                    builder = WeightingMethod.factor_based(Factor(factor))
                except ValueError:
                    logger.warning(f"Unknown factor: {factor}, defaulting to market cap")
                    builder = WeightingMethod.market_cap()
            else:
                builder = WeightingMethod.market_cap()
        else:
            builder = WeightingMethod.market_cap()

        # Apply caps
        caps = config.get("caps", {})
        if caps:
            max_weight = caps.get("max_weight")
            max_sector = caps.get("max_weight_per_sector")
            max_country = caps.get("max_weight_per_country")

            if any([max_weight, max_sector, max_country]):
                builder.with_cap(
                    max_weight=max_weight,
                    max_weight_per_sector=max_sector,
                    max_weight_per_country=max_country,
                )

        return builder.build()

    def _build_rebalancing_schedule(self, config: dict) -> Optional[RebalancingSchedule]:
        """Build RebalancingSchedule from configuration."""
        if not config:
            return None

        frequency = config.get("frequency", "QUARTERLY").upper()

        if frequency == "MONTHLY":
            return RebalancingSchedule.monthly(day=config.get("day", 1))
        elif frequency == "QUARTERLY":
            return RebalancingSchedule.quarterly()
        elif frequency == "SEMI_ANNUAL":
            return RebalancingSchedule.semi_annual(
                months=config.get("months", [6, 12]),
                day=config.get("day", 15),
            )
        elif frequency == "ANNUAL":
            return RebalancingSchedule.annual(
                month=config.get("months", [12])[0] if config.get("months") else 12,
                day=config.get("day", 15),
            )
        else:
            # Custom schedule
            builder = RebalancingSchedule.builder()
            builder.frequency(frequency)

            months = config.get("months")
            if months:
                builder.on_months(months)

            day = config.get("day")
            if day:
                builder.on_day(day)

            return builder.build()


# Convenience function for quick index creation
def create_index_from_description(
    description: str,
    api_key: Optional[str] = None,
    **kwargs,
) -> Index:
    """
    Create an index from a natural language description.

    This is a convenience function that creates an IndexAI instance
    and immediately creates an index.

    Args:
        description: Natural language description of the desired index
        api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        **kwargs: Additional arguments passed to create_index()

    Returns:
        The created Index object

    Example:
        >>> from indexforge.ai import create_index_from_description
        >>>
        >>> index = create_index_from_description(
        ...     "Top 30 European banks by market cap, equal weighted"
        ... )
    """
    ai = IndexAI(api_key=api_key)
    result = ai.create_index(description, **kwargs)
    return result.index
