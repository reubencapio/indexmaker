# Index Maker - Module Structure & Architecture

## Overview

This document outlines the proposed module structure for the Index Maker library, showing how different components are organized and how they interact.

## Package Structure

```
indexmaker/
│
├── __init__.py                 # Main exports
│
├── core/                       # Core domain models
│   ├── __init__.py
│   ├── index.py               # Index class
│   ├── universe.py            # Universe definition
│   ├── constituent.py         # Constituent model
│   ├── currency.py            # Currency handling
│   └── index_type.py          # Index type enums
│
├── selection/                  # Selection strategies
│   ├── __init__.py
│   ├── criteria.py            # SelectionCriteria class
│   ├── factors.py             # Factor definitions
│   ├── ranking.py             # Ranking methods
│   ├── composite.py           # Composite scoring
│   └── custom.py              # Custom rule support
│
├── weighting/                  # Weighting methodologies
│   ├── __init__.py
│   ├── methods.py             # WeightingMethod classes
│   ├── equal_weight.py        # Equal weighting
│   ├── market_cap.py          # Market cap weighting
│   ├── factor_based.py        # Factor-based weighting
│   ├── custom.py              # Custom weighting
│   └── caps.py                # Capping mechanisms
│
├── rebalancing/                # Rebalancing logic
│   ├── __init__.py
│   ├── schedule.py            # RebalancingSchedule class
│   ├── rules.py               # Rebalancing rules
│   ├── buffer.py              # Buffer mechanisms
│   └── extraordinary.py       # Extraordinary rebalancing
│
├── calculation/                # Index calculation
│   ├── __init__.py
│   ├── engine.py              # Main calculation engine
│   ├── divisor.py             # Divisor adjustments
│   ├── returns.py             # Return calculations
│   └── currency_hedging.py    # Currency hedging logic
│
├── corporate_actions/          # Corporate actions handling
│   ├── __init__.py
│   ├── policy.py              # CorporateActions policy
│   ├── dividends.py           # Dividend handling
│   ├── splits.py              # Stock splits
│   ├── mergers.py             # Mergers & acquisitions
│   └── spin_offs.py           # Spin-offs
│
├── data/                       # Data integration
│   ├── __init__.py
│   ├── provider.py            # DataProvider class
│   ├── sources.py             # Data source connectors
│   ├── bloomberg.py           # Bloomberg integration
│   ├── refinitiv.py           # Refinitiv integration
│   ├── factset.py             # FactSet integration
│   └── cache.py               # Data caching
│
├── validation/                 # Validation & compliance
│   ├── __init__.py
│   ├── rules.py               # ValidationRules class
│   ├── constraints.py         # Constraint checking
│   ├── compliance.py          # Compliance checks
│   └── report.py              # Validation reporting
│
├── backtesting/                # Backtesting & simulation
│   ├── __init__.py
│   ├── backtest.py            # Backtest class
│   ├── simulator.py           # Simulation engine
│   ├── performance.py         # Performance metrics
│   └── comparison.py          # Benchmark comparison
│
├── documentation/              # Document generation
│   ├── __init__.py
│   ├── generator.py           # DocumentGenerator class
│   ├── templates/             # Document templates
│   │   ├── guideline.html
│   │   ├── factsheet.html
│   │   └── methodology.html
│   ├── guideline.py           # Guideline generation
│   ├── factsheet.py           # Factsheet generation
│   └── methodology.py         # Methodology docs
│
├── publishing/                 # Data publishing
│   ├── __init__.py
│   ├── publisher.py           # Publisher class
│   ├── bloomberg_feed.py      # Bloomberg data feed
│   ├── refinitiv_feed.py      # Refinitiv data feed
│   ├── api_endpoint.py        # API publishing
│   └── website.py             # Website publishing
│
├── events/                     # Event system
│   ├── __init__.py
│   ├── event.py               # Event definitions
│   ├── listener.py            # Event listeners
│   └── dispatcher.py          # Event dispatcher
│
├── utils/                      # Utilities
│   ├── __init__.py
│   ├── dates.py               # Date utilities
│   ├── business_days.py       # Business day calculations
│   ├── formatting.py          # Formatting utilities
│   └── serialization.py       # JSON/YAML serialization
│
├── exceptions/                 # Custom exceptions
│   ├── __init__.py
│   ├── validation_errors.py   # Validation exceptions
│   ├── calculation_errors.py  # Calculation exceptions
│   └── data_errors.py         # Data access exceptions
│
└── types/                      # Type definitions
    ├── __init__.py
    ├── enums.py               # Enum definitions
    └── protocols.py           # Protocol definitions (interfaces)
```

---

## Component Architecture

### Layer 1: User-Facing API

```
┌─────────────────────────────────────────────────┐
│             User Code                           │
│                                                 │
│  index = Index.create(...)                      │
│  universe = Universe.builder()...               │
│  index.set_universe(universe)                   │
│  index_value = index.calculate()                │
└─────────────────────────────────────────────────┘
                    ↓
```

### Layer 2: Domain Model

```
┌─────────────────────────────────────────────────┐
│           Domain Model Layer                    │
│                                                 │
│  Index ← Universe ← Constituent                 │
│    ↓                                            │
│  SelectionCriteria ← Factor                     │
│  WeightingMethod                                │
│  RebalancingSchedule                            │
│  CorporateActionsPolicy                         │
└─────────────────────────────────────────────────┘
                    ↓
```

### Layer 3: Business Logic

```
┌─────────────────────────────────────────────────┐
│         Business Logic Layer                    │
│                                                 │
│  Selection Engine → Ranking → Filtering         │
│  Weighting Engine → Caps → Normalization        │
│  Rebalancing Engine → Buffer Rules              │
│  Calculation Engine → Divisor Adjustment        │
└─────────────────────────────────────────────────┘
                    ↓
```

### Layer 4: Data Access

```
┌─────────────────────────────────────────────────┐
│           Data Access Layer                     │
│                                                 │
│  DataProvider → Market Data                     │
│              → Corporate Actions                │
│              → Fundamentals                     │
│              → ESG Data                         │
└─────────────────────────────────────────────────┘
                    ↓
```

### Layer 5: Infrastructure

```
┌─────────────────────────────────────────────────┐
│        Infrastructure Layer                     │
│                                                 │
│  Validation → Persistence → Events              │
│  Caching → Serialization → Logging              │
└─────────────────────────────────────────────────┘
```

---

## Key Classes and Their Responsibilities

### Core Classes

#### `Index`
**Responsibility**: Main entry point, orchestrates all index operations

```python
class Index:
    def __init__(self, name, identifier, currency, base_date, base_value)
    
    # Configuration
    def set_universe(self, universe: Universe) -> Index
    def set_selection_criteria(self, criteria: SelectionCriteria) -> Index
    def set_weighting_method(self, method: WeightingMethod) -> Index
    def set_rebalancing_schedule(self, schedule: RebalancingSchedule) -> Index
    
    # Calculation
    def calculate(self, date: str) -> float
    def get_constituents(self, date: str) -> List[Constituent]
    def get_performance(self, start_date: str, end_date: str) -> Performance
    
    # Analysis
    def backtest(self, start_date: str, end_date: str) -> Backtest
    def validate(self) -> ValidationReport
    
    # Lifecycle
    def save(self, path: str) -> None
    @classmethod
    def load(cls, path: str) -> Index
```

#### `Universe`
**Responsibility**: Defines the investment universe

```python
class Universe:
    @staticmethod
    def builder() -> UniverseBuilder
    
    @staticmethod
    def from_tickers(tickers: List[str]) -> Universe
    
    def get_eligible_securities(self, date: str) -> List[Security]
    def validate(self) -> bool

class UniverseBuilder:
    def asset_class(self, asset_class: AssetClass) -> UniverseBuilder
    def regions(self, regions: List[Region]) -> UniverseBuilder
    def sectors(self, sectors: List[str]) -> UniverseBuilder
    def min_market_cap(self, amount: float) -> UniverseBuilder
    def esg_screening(self, **criteria) -> UniverseBuilder
    def build() -> Universe
```

#### `SelectionCriteria`
**Responsibility**: Defines how constituents are selected

```python
class SelectionCriteria:
    @staticmethod
    def builder() -> SelectionCriteriaBuilder
    
    @staticmethod
    def top_by_market_cap(n: int) -> SelectionCriteria
    
    def select(self, universe: List[Security], date: str) -> List[Constituent]

class SelectionCriteriaBuilder:
    def ranking_by(self, factor: Factor) -> SelectionCriteriaBuilder
    def composite_score(self, score: CompositeScore) -> SelectionCriteriaBuilder
    def select_top(self, n: int) -> SelectionCriteriaBuilder
    def apply_buffer_rules(self, ...) -> SelectionCriteriaBuilder
    def build() -> SelectionCriteria
```

#### `WeightingMethod`
**Responsibility**: Defines how constituents are weighted

```python
class WeightingMethod:
    @staticmethod
    def equal_weight() -> WeightingMethod
    
    @staticmethod
    def market_cap() -> WeightingMethodBuilder
    
    @staticmethod
    def free_float_market_cap() -> WeightingMethod
    
    def calculate_weights(self, constituents: List[Constituent]) -> Dict[str, float]

class WeightingMethodBuilder:
    def with_cap(self, max_weight: float) -> WeightingMethodBuilder
    def build() -> WeightingMethod
```

#### `RebalancingSchedule`
**Responsibility**: Defines when and how rebalancing occurs

```python
class RebalancingSchedule:
    @staticmethod
    def quarterly() -> RebalancingSchedule
    
    @staticmethod
    def annual(month: int, day: int) -> RebalancingSchedule
    
    @staticmethod
    def builder() -> RebalancingScheduleBuilder
    
    def get_rebalancing_dates(self, start: str, end: str) -> List[str]

class RebalancingScheduleBuilder:
    def frequency(self, freq: str) -> RebalancingScheduleBuilder
    def on_months(self, months: List[int]) -> RebalancingScheduleBuilder
    def on_day(self, day: int) -> RebalancingScheduleBuilder
    def build() -> RebalancingSchedule
```

---

## Data Flow Diagrams

### Index Calculation Flow

```
User Request: index.calculate(date="2025-11-15")
    ↓
┌─────────────────────────────┐
│ Index                       │
│ - Validate date             │
│ - Check if calculation      │
│   already exists (cache)    │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Get Constituents            │
│ - Apply selection criteria  │
│ - Apply weighting method    │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Data Provider               │
│ - Fetch prices              │
│ - Fetch corporate actions   │
│ - Fetch market data         │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Calculation Engine          │
│ - Calculate index value     │
│ - Apply divisor adjustment  │
│ - Handle corporate actions  │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Return Result               │
│ - Cache result              │
│ - Trigger events            │
│ - Return index value        │
└─────────────────────────────┘
```

### Rebalancing Flow

```
Rebalancing Date Reached
    ↓
┌─────────────────────────────┐
│ RebalancingSchedule         │
│ - Check if rebalancing due  │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Universe                    │
│ - Get eligible securities   │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ SelectionCriteria           │
│ - Apply ranking             │
│ - Apply buffer rules        │
│ - Select new constituents   │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ WeightingMethod             │
│ - Calculate weights         │
│ - Apply caps                │
│ - Normalize                 │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Index                       │
│ - Update constituents       │
│ - Adjust divisor            │
│ - Trigger events            │
└─────────────────────────────┘
```

---

## Extension Points

### Custom Selection Rules

```python
from indexmaker import CustomRule, RuleContext

@CustomRule.selection
def my_custom_filter(context: RuleContext) -> bool:
    """Custom logic for selecting constituents."""
    security = context.security
    # Your custom logic
    return True  # Include or False to exclude

# Use in selection criteria
selection = (SelectionCriteria.builder()
    .custom_filter(my_custom_filter)
    .select_top(50)
    .build()
)
```

### Custom Weighting

```python
from indexmaker import CustomWeighting

class MyWeightingMethod(CustomWeighting):
    def calculate_weights(self, constituents: List[Constituent]) -> Dict[str, float]:
        # Your custom weighting logic
        weights = {}
        for c in constituents:
            weights[c.identifier] = self._calculate_weight(c)
        return self._normalize(weights)

# Use custom weighting
weighting = MyWeightingMethod(...)
index.set_weighting_method(weighting)
```

### Custom Data Source

```python
from indexmaker import DataConnector

class MyDataConnector(DataConnector):
    def get_prices(self, identifiers: List[str], date: str) -> pd.DataFrame:
        # Your data fetching logic
        pass
    
    def get_market_data(self, identifiers: List[str], date: str) -> pd.DataFrame:
        # Your market data logic
        pass

# Use custom connector
data_provider = (DataProvider.builder()
    .add_custom_source("my_source", MyDataConnector())
    .build()
)
index.set_data_provider(data_provider)
```

### Event Handlers

```python
from indexmaker import IndexEvent

@index.on(IndexEvent.CONSTITUENT_ADDED)
def on_constituent_added(event):
    # Your logic when constituent is added
    print(f"Added: {event.constituent.name}")
    # Could send notification, update database, etc.

@index.on(IndexEvent.REBALANCING_COMPLETED)
def on_rebalancing_completed(event):
    # Your logic after rebalancing
    print(f"Rebalancing done. Turnover: {event.turnover:.2%}")
```

---

## Testing Strategy

### Unit Tests
```python
# Test individual components in isolation
def test_universe_builder():
    universe = (Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .min_market_cap(1_000_000_000)
        .build()
    )
    assert universe.min_market_cap == 1_000_000_000

def test_market_cap_weighting():
    weighting = WeightingMethod.market_cap()
    constituents = [...]  # Mock constituents
    weights = weighting.calculate_weights(constituents)
    assert sum(weights.values()) == 1.0
```

### Integration Tests
```python
# Test components working together
def test_index_calculation():
    index = Index.create(...)
    index.set_universe(test_universe)
    index.set_selection_criteria(test_criteria)
    index.set_weighting_method(test_weighting)
    
    value = index.calculate(date="2025-11-15")
    assert value > 0
```

### End-to-End Tests
```python
# Test complete workflows
def test_full_index_lifecycle():
    # Create
    index = create_test_index()
    
    # Configure
    configure_test_index(index)
    
    # Validate
    assert index.validate().is_valid
    
    # Backtest
    backtest = index.backtest(...)
    assert backtest.sharpe_ratio > 0
    
    # Generate documents
    guideline = generate_guideline(index)
    assert guideline.exists()
```

---

## Configuration Management

### Index Configuration File (JSON/YAML)

```json
{
  "name": "Tech Leaders Index",
  "identifier": "TECHLDRS",
  "currency": "USD",
  "base_date": "2025-01-01",
  "base_value": 1000.0,
  "universe": {
    "asset_class": "EQUITIES",
    "regions": ["NORTH_AMERICA", "EUROPE"],
    "sectors": ["Technology"],
    "min_market_cap": 1000000000,
    "esg_screening": {
      "min_esg_score": 70,
      "exclude_controversial_weapons": true
    }
  },
  "selection": {
    "ranking_by": "MARKET_CAP",
    "select_top": 50,
    "buffer_rules": {
      "add_threshold": 45,
      "remove_threshold": 60
    }
  },
  "weighting": {
    "method": "MARKET_CAP",
    "caps": {
      "max_weight": 0.10
    }
  },
  "rebalancing": {
    "frequency": "quarterly",
    "months": [3, 6, 9, 12],
    "day": 15
  }
}
```

### Loading Configuration

```python
# Load from file
index = Index.from_config_file("index_config.json")

# Or from dict
config = {...}
index = Index.from_config(config)

# Export configuration
index.to_config_file("index_config.json")
```

---

## Performance Considerations

### Caching Strategy
- Cache calculated index values
- Cache constituent data
- Cache market data (with TTL)
- Invalidate cache on configuration changes

### Lazy Loading
- Load data only when needed
- Defer expensive calculations
- Use generators for large datasets

### Parallel Processing
- Parallel data fetching
- Parallel backtesting
- Parallel document generation

---

## Summary

This module structure provides:

1. **Clear Separation of Concerns**: Each module has a specific responsibility
2. **Extensibility**: Easy to add new features through well-defined extension points
3. **Testability**: Components can be tested in isolation
4. **Maintainability**: Clear organization makes code easy to navigate
5. **Performance**: Caching and lazy loading for efficiency
6. **Flexibility**: Support for custom logic at key points
7. **Production-Ready**: Comprehensive error handling, validation, and logging

The architecture follows SOLID principles and uses design patterns appropriate for financial index management systems.



