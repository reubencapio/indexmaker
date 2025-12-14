# Index Maker - Quick Reference Guide

## Common Patterns Cheat Sheet

### Basic Index Creation

```python
from indexmaker import Index, Currency, IndexType

index = Index.create(
    name="My Index",
    identifier="MYIDX",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)
```

---

## Universe Definitions

### Simple Universe
```python
from indexmaker import Universe, AssetClass, Region

universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .regions([Region.NORTH_AMERICA])
    .min_market_cap(1_000_000_000)
    .build()
)
```

### With ESG Screening
```python
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .esg_screening(
        min_esg_score=70,
        exclude_controversial_weapons=True,
        exclude_tobacco=True
    )
    .build()
)
```

### From Ticker List
```python
universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL"])
```

---

## Selection Methods

### Top N by Market Cap
```python
from indexmaker import SelectionCriteria, Factor

selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .build()
)
```

### With Buffer Rules
```python
selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .apply_buffer_rules(
        add_threshold=45,
        remove_threshold=60
    )
    .build()
)
```

### Multi-Factor Selection
```python
from indexmaker import CompositeScore

selection = (SelectionCriteria.builder()
    .composite_score(
        CompositeScore.builder()
            .add_factor(Factor.VALUE, weight=0.4)
            .add_factor(Factor.MOMENTUM, weight=0.3)
            .add_factor(Factor.QUALITY, weight=0.3)
            .build()
    )
    .select_top(100)
    .build()
)
```

---

## Weighting Methods

### Equal Weight
```python
from indexmaker import WeightingMethod

weighting = WeightingMethod.equal_weight()
```

### Market Cap with Cap
```python
weighting = (WeightingMethod.market_cap()
    .with_cap(max_weight=0.10)
    .build()
)
```

### Free-Float Market Cap
```python
weighting = WeightingMethod.free_float_market_cap()
```

### Factor-Based
```python
weighting = (WeightingMethod.factor_based()
    .factor(Factor.DIVIDEND_YIELD)
    .with_cap(max_weight=0.08)
    .build()
)
```

---

## Rebalancing Schedules

### Quarterly
```python
from indexmaker import RebalancingSchedule

rebalancing = RebalancingSchedule.quarterly()
# Or with specific months
rebalancing = (RebalancingSchedule.builder()
    .frequency("quarterly")
    .on_months([3, 6, 9, 12])
    .on_day(15)
    .build()
)
```

### Annual
```python
rebalancing = RebalancingSchedule.annual(month=12, day=31)
```

### Monthly
```python
rebalancing = RebalancingSchedule.monthly(day=1)
```

---

## Complete Example - Copy & Modify

```python
from indexmaker import (
    Index, Currency, IndexType,
    Universe, AssetClass, Region,
    SelectionCriteria, Factor,
    WeightingMethod,
    RebalancingSchedule
)

# 1. Create index
index = Index.create(
    name="Example Index",
    identifier="SOLEXIDX",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0,
    index_type=IndexType.PRICE_RETURN
)

# 2. Define universe
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .regions([Region.NORTH_AMERICA, Region.EUROPE])
    .min_market_cap(500_000_000)
    .min_free_float(0.15)
    .build()
)

# 3. Selection criteria
selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .apply_buffer_rules(add_threshold=45, remove_threshold=60)
    .build()
)

# 4. Weighting
weighting = (WeightingMethod.market_cap()
    .with_cap(max_weight=0.10)
    .build()
)

# 5. Rebalancing
rebalancing = RebalancingSchedule.quarterly()

# 6. Configure
(index
    .set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
    .set_rebalancing_schedule(rebalancing)
)

# 7. Calculate
value = index.calculate(date="2025-11-15")
print(f"Index value: {value}")
```

---

## Common Operations

### Get Index Value
```python
value = index.calculate(date="2025-11-15")
```

### Get Constituents
```python
constituents = index.get_constituents(date="2025-11-15")
for c in constituents:
    print(f"{c.name}: {c.weight:.2%}")
```

### Get Performance
```python
perf = index.get_performance(
    start_date="2025-01-01",
    end_date="2025-11-15"
)
print(f"Return: {perf.total_return:.2%}")
```

### Get Time Series
```python
ts = index.get_timeseries(
    start_date="2025-01-01",
    end_date="2025-11-15",
    frequency="daily"
)
```

### Backtest
```python
backtest = index.backtest(
    start_date="2020-01-01",
    end_date="2024-12-31",
    initial_value=1000.0
)
print(f"Sharpe: {backtest.sharpe_ratio:.2f}")
```

### Generate Documents
```python
from indexmaker import DocumentGenerator

DocumentGenerator.for_index(index).generate("GUIDELINE").save_to("guideline.pdf")
DocumentGenerator.for_index(index).generate("FACTSHEET").save_to("factsheet.pdf")
```

### Save/Load Index
```python
# Save
index.save("my_index.json")

# Load
index = Index.load("my_index.json")
```

---

## Advanced Patterns

### Custom Data Source
```python
from indexmaker import DataProvider

data_provider = (DataProvider.builder()
    .market_data("Bloomberg")
    .add_custom_source(
        name="my_data",
        connector=my_connector
    )
    .build()
)
index.set_data_provider(data_provider)
```

### Validation Rules
```python
from indexmaker import ValidationRules

validation = (ValidationRules.builder()
    .min_constituents(30)
    .max_constituents(50)
    .max_single_constituent_weight(0.10)
    .build()
)
index.set_validation_rules(validation)
```

### Create Variants
```python
# Total return variant
tr_index = index.create_variant(
    variant_type=IndexType.TOTAL_RETURN,
    identifier="MYIDXTR"
)

# Currency hedged
hedged = index.create_variant(
    variant_type=IndexType.CURRENCY_HEDGED,
    target_currency=Currency.EUR
)
```

### Event Listeners
```python
@index.on("CONSTITUENT_ADDED")
def on_added(event):
    print(f"Added: {event.constituent.name}")

@index.on("REBALANCING_COMPLETED")
def on_rebalance(event):
    print(f"Turnover: {event.turnover:.2%}")
```

---

## Enums & Constants Reference

### Currency
```python
Currency.USD, Currency.EUR, Currency.GBP, Currency.JPY, Currency.CHF
```

### IndexType
```python
IndexType.PRICE_RETURN
IndexType.TOTAL_RETURN
IndexType.NET_RETURN
IndexType.CURRENCY_HEDGED
```

### AssetClass
```python
AssetClass.EQUITIES
AssetClass.BONDS
AssetClass.COMMODITIES
AssetClass.CURRENCIES
AssetClass.ALTERNATIVES
```

### Region
```python
Region.GLOBAL
Region.NORTH_AMERICA
Region.EUROPE
Region.ASIA_PACIFIC
Region.EMERGING_MARKETS
Region.DEVELOPED_MARKETS
```

### Factor
```python
Factor.MARKET_CAP
Factor.LIQUIDITY
Factor.MOMENTUM
Factor.VALUE
Factor.QUALITY
Factor.LOW_VOLATILITY
Factor.DIVIDEND_YIELD
Factor.EARNINGS_GROWTH
```

---

## Tips & Best Practices

1. **Use Builder Pattern**: More readable than many parameters
   ```python
   # Good
   universe = Universe.builder().asset_class(...).regions(...).build()
   
   # Less clear
   universe = Universe(asset_class=..., regions=...)
   ```

2. **Chain Configuration**: More fluent
   ```python
   (index
       .set_universe(universe)
       .set_selection_criteria(selection)
       .set_weighting_method(weighting)
   )
   ```

3. **Validate Early**: Check configuration before backtesting
   ```python
   report = index.validate()
   if not report.is_valid:
       print(report.errors)
   ```

4. **Use Type Hints**: Better IDE support
   ```python
   from typing import List
   from indexmaker import Constituent
   
   def analyze(constituents: List[Constituent]) -> float:
       ...
   ```

5. **Save Configurations**: Reuse and version control
   ```python
   index.save("production_index.json")
   # Commit to git for versioning
   ```



