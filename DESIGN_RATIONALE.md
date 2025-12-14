# Design Rationale - Why This API Design?

This document explains the design decisions behind the Index Maker API and compares different approaches.

## Core Design Decision: Domain-Driven Language

### ❌ Code-Centric Approach (Anti-Pattern)
```python
# Technical jargon, not domain language
calculator = Calculator()
calculator.set_input_data(stocks)
calculator.set_weights([0.1, 0.2, 0.3, 0.4])
calculator.set_rebalance_freq(90)  # What does 90 mean?
result = calculator.compute()
```

**Problems:**
- Uses technical terms (calculator, compute) instead of domain terms
- Magic numbers (90 - days? months?)
- Unclear what "result" represents
- Doesn't match how index professionals think

### ✅ Domain-Driven Approach (Our Design)
```python
# Clear domain language
index = Index.create(name="Tech Leaders", ...)
index.set_universe(Universe.from_sectors(["Technology"]))
index.set_selection_criteria(SelectionCriteria.top_by_market_cap(50))
index.set_weighting_method(WeightingMethod.equal_weight())
index.set_rebalancing_schedule(RebalancingSchedule.quarterly())
index_value = index.calculate(date="2025-11-15")
```

**Benefits:**
- Uses industry terminology (universe, constituents, rebalancing)
- Self-documenting code
- Reads like a conversation with an index expert
- Clear intent and purpose

---

## Design Pattern Comparisons

### 1. Object Creation Patterns

#### ❌ Constructor with Many Parameters
```python
# Hard to read, easy to mix up parameters
index = Index(
    "Tech Index",
    "TECH",
    "USD",
    1000,
    "2025-01-01",
    "PR",
    None,
    None,
    "DE000ABC123",
    True,
    False
)
# Which parameter is which? Hard to remember order.
```

#### ❌ Setters Without Chaining
```python
# Verbose and repetitive
index = Index()
index.set_name("Tech Index")
index.set_identifier("TECH")
index.set_currency("USD")
index.set_base_value(1000)
index.set_base_date("2025-01-01")
# Gets tedious quickly
```

#### ✅ Factory Method + Builder Pattern (Our Design)
```python
# Clear, readable, maintainable
index = Index.create(
    name="Tech Index",
    identifier="TECH",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)

# For complex objects, use builder
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .regions([Region.NORTH_AMERICA])
    .min_market_cap(1_000_000_000)
    .build()
)
```

**Why Better:**
- Named parameters make intent clear
- Can't mix up parameter order
- Optional parameters have good defaults
- Builder pattern for complex objects
- Type-safe with enums

---

### 2. Configuration Patterns

#### ❌ Dictionary/JSON Configuration
```python
# Prone to typos, no validation, no autocomplete
config = {
    "universe": {
        "asset_class": "equities",  # Typo: should be EQUITIES?
        "regions": ["US", "EU"],     # Inconsistent: US vs USA?
        "min_mkt_cap": 1000000000,   # Abbreviated field name
    },
    "selection": {
        "method": "top_n",
        "n": 50,
        "factor": "market_cap"
    }
}
index.configure(config)
```

**Problems:**
- Typos discovered at runtime
- No IDE autocomplete
- Inconsistent naming conventions
- No type checking
- No validation until execution

#### ✅ Typed Objects with Builders (Our Design)
```python
# Type-safe, validated, autocomplete-friendly
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)  # Enum - can't typo
    .regions([Region.NORTH_AMERICA])    # Standardized
    .min_market_cap(1_000_000_000)     # Clear name
    .build()                            # Validates on build
)

selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)     # Type-safe
    .select_top(50)                     # Clear intent
    .build()
)
```

**Benefits:**
- IDE autocomplete
- Type checking catches errors
- Validation on build
- Can't use invalid values
- Self-documenting

---

### 3. Method Naming Conventions

#### ❌ Generic/Unclear Names
```python
index.set_data([...])        # What kind of data?
index.process()              # Process what? How?
index.get_result()           # What result?
index.update(123)            # Update what with 123?
```

#### ❌ Too Technical
```python
index.set_weight_vector([...])    # "vector" is implementation detail
index.execute_algorithm()          # What algorithm?
index.apply_transformation()       # What transformation?
```

#### ✅ Domain-Specific Names (Our Design)
```python
index.set_universe(...)               # Clear: defines what's in scope
index.set_selection_criteria(...)    # Clear: how to choose constituents
index.set_weighting_method(...)      # Clear: how to weight them
index.calculate(date="2025-11-15")   # Clear: compute index value
index.get_constituents(...)          # Clear: get current members
index.rebalance(...)                 # Clear: restructure the index
```

**Benefits:**
- Matches domain terminology
- No guessing what method does
- Discoverable through autocomplete
- Self-documenting

---

### 4. Error Handling Approaches

#### ❌ Silent Failures or Generic Errors
```python
index.set_universe(invalid_data)
# Later...
index.calculate()  # Fails with: "Error: Invalid data"
# What was invalid? Where? How to fix?
```

#### ❌ Exception Chaos
```python
try:
    index.calculate()
except Exception as e:  # Too generic
    print(e)  # Unhelpful message
```

#### ✅ Validation + Domain-Specific Exceptions (Our Design)
```python
# Early validation
validation_report = index.validate()
if not validation_report.is_valid:
    for error in validation_report.errors:
        print(f"{error.field}: {error.message}")
        print(f"  Current value: {error.current_value}")
        print(f"  Expected: {error.expected}")
        print(f"  Suggestion: {error.suggestion}")

# Or specific exceptions
from indexmaker.exceptions import (
    InsufficientConstituentsError,
    WeightCapViolationError,
    InvalidUniverseError
)

try:
    index.calculate()
except InsufficientConstituentsError as e:
    print(f"Not enough constituents: {e.current_count} < {e.required_count}")
    print(f"Suggestion: {e.suggestion}")
```

**Benefits:**
- Fail early with validation
- Clear, actionable error messages
- Specific exception types
- Includes suggestions for fixes

---

### 5. Data Access Patterns

#### ❌ Generic Getters
```python
data = index.get_data()  # Returns what exactly?
info = index.get_info()  # Too vague
```

#### ❌ Nested Data Structures
```python
# Hard to work with
result = index.calculate()
value = result["data"]["index"]["value"]["close"]
constituents = result["data"]["constituents"]["list"]
```

#### ✅ Specific, Typed Methods (Our Design)
```python
# Clear and type-safe
index_value: float = index.calculate(date="2025-11-15")

constituents: List[Constituent] = index.get_constituents(date="2025-11-15")
for c in constituents:
    print(f"{c.name}: {c.ticker}, Weight: {c.weight:.2%}")

performance: Performance = index.get_performance(
    start_date="2025-01-01",
    end_date="2025-11-15"
)
print(f"Return: {performance.total_return:.2%}")
print(f"Volatility: {performance.volatility:.2%}")

timeseries: pd.DataFrame = index.get_timeseries(
    start_date="2025-01-01",
    end_date="2025-11-15",
    frequency="daily"
)
```

**Benefits:**
- Type hints guide usage
- Clear return types
- Specific methods for specific needs
- Works well with data analysis tools

---

## Fluent Interface vs. Configuration Object

### ❌ Large Configuration Object
```python
# All at once, hard to build incrementally
config = IndexConfiguration(
    universe=UniverseConfig(...),
    selection=SelectionConfig(...),
    weighting=WeightingConfig(...),
    rebalancing=RebalancingConfig(...),
    calculation=CalculationConfig(...),
    # ... many more nested configs
)
index = Index(config)
```

**Problems:**
- Must know entire structure upfront
- Hard to modify incrementally
- Testing is difficult (need complete config)
- Not discoverable

### ✅ Fluent Chainable Interface (Our Design)
```python
# Build incrementally, discoverable through IDE
index = (Index.create(...)
    .set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
    .set_rebalancing_schedule(rebalancing)
)

# Easy to modify
index.set_weighting_method(new_weighting)

# Easy to test individual components
def test_universe():
    universe = Universe.builder().asset_class(...).build()
    assert universe.validate()
```

**Benefits:**
- Build step by step
- IDE autocomplete at each step
- Easy to modify
- Each component testable
- Natural, readable flow

---

## Simple vs. Powerful

### Design Goal: Progressive Disclosure

#### Level 1: Simple Use Case (4 lines)
```python
index = Index.create("Simple Index", "SIMPLE", Currency.USD, "2025-01-01", 1000)
index.set_universe(Universe.from_tickers(["AAPL", "MSFT", "GOOGL"]))
index.set_weighting_method(WeightingMethod.equal_weight())
print(index.calculate(date="2025-11-15"))
```

#### Level 2: Moderate Complexity (15 lines)
```python
index = Index.create(...)
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .sectors(["Technology"])
    .min_market_cap(1_000_000_000)
    .build()
)
selection = SelectionCriteria.top_by_market_cap(50)
weighting = WeightingMethod.market_cap().with_cap(0.10).build()
rebalancing = RebalancingSchedule.quarterly()

index.set_universe(universe)
index.set_selection_criteria(selection)
index.set_weighting_method(weighting)
index.set_rebalancing_schedule(rebalancing)
```

#### Level 3: Advanced Use Case (50+ lines)
```python
# Multi-factor, ESG-screened, with custom rules, event handlers, etc.
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .esg_screening(min_score=70, exclude_controversial=True)
    .custom_filter(my_proprietary_filter)
    .build()
)

selection = (SelectionCriteria.composite_score()
    .add_factor(Factor.VALUE, 0.3)
    .add_factor(Factor.QUALITY, 0.3)
    .add_custom_factor(my_innovation_score, 0.4)
    .select_top(100)
    .diversification_constraint(max_per_country=15)
    .build()
)

@index.on(IndexEvent.REBALANCING_COMPLETED)
def on_rebalance(event):
    notify_stakeholders(event)

# ... many more advanced features
```

**Key Principle:**
- Simple things are simple
- Complex things are possible
- Complexity is opt-in, not forced

---

## Type Safety Comparison

### ❌ Stringly-Typed (String-based)
```python
index.set_currency("usd")  # or "USD"? "dollars"?
index.set_region("north_america")  # or "North America"? "NA"?
index.set_frequency("quarterly")  # or "Quarterly"? "Q"? "3M"?
# No validation until runtime
```

### ❌ Magic Numbers
```python
index.set_frequency(3)  # 3 what? months? quarters? times per year?
index.set_region(1)     # 1 means... North America?
```

### ✅ Enums and Constants (Our Design)
```python
index.set_currency(Currency.USD)           # Clear, can't typo
index.set_region(Region.NORTH_AMERICA)     # Autocomplete shows options
index.set_frequency(Frequency.QUARTERLY)   # Self-documenting

# Can't use invalid value
index.set_currency(Currency.INVALID)  # IDE catches this
```

**Benefits:**
- Type checker catches errors
- IDE autocomplete
- Self-documenting
- Refactoring is safe
- Can't use invalid values

---

## API Evolution: Good Defaults

### ❌ Everything Required
```python
# Too many required parameters
index = Index(
    name="Tech",
    identifier="TECH",
    currency="USD",
    base_date="2025-01-01",
    base_value=1000,
    # Must specify even if using defaults
    rounding=2,
    price_source="closing",
    divisor_method="chain_linked",
    calculate_tr=False,
    calculate_nr=False,
    # ... 20 more parameters
)
```

### ✅ Smart Defaults (Our Design)
```python
# Only specify what matters
index = Index.create(
    name="Tech Index",
    identifier="TECH",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)
# Everything else has sensible defaults

# Override only when needed
calculation = (CalculationMethod.builder()
    .include_total_return_variant(True)  # Override default
    .build()
)
```

**Benefits:**
- Quick to get started
- Less boilerplate
- Flexibility when needed
- Defaults follow best practices

---

## Real-World Example Comparison

### Scenario: Create a market cap weighted ESG-screened index

#### ❌ Poor API Design
```python
idx = Idx()
idx.nm = "ESG Tech"
idx.id = "ESGTECH"
idx.init(1000, "2025-01-01", "USD")
cfg = {"type": "eq", "region": ["US", "EU"], "esg": 70}
idx.set_cfg(cfg)
idx.sel_method = "top"
idx.sel_n = 50
idx.wgt_method = "mcap"
idx.wgt_cap = 0.1
idx.calc()
```

**Problems:**
- Abbreviated names
- Mixed configuration styles
- No validation
- No autocomplete
- Hard to understand

#### ✅ Our API Design
```python
from indexmaker import (
    Index, Currency, Universe, AssetClass, Region,
    SelectionCriteria, Factor, WeightingMethod
)

index = Index.create(
    name="ESG Tech Index",
    identifier="ESGTECH",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)

universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .regions([Region.NORTH_AMERICA, Region.EUROPE])
    .sectors(["Technology"])
    .esg_screening(min_esg_score=70)
    .build()
)

selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .build()
)

weighting = (WeightingMethod.market_cap()
    .with_cap(max_weight=0.10)
    .build()
)

(index
    .set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
)

index_value = index.calculate(date="2025-11-15")
```

**Benefits:**
- Crystal clear intent
- Self-documenting
- Type-safe
- Validated
- IDE support
- Easy to modify
- Easy to test
- Professional quality code

---

## Summary: Why This Design Wins

| Aspect | Our Design | Alternative Approaches |
|--------|------------|----------------------|
| **Readability** | ✅ Reads like domain language | ❌ Technical jargon |
| **Discoverability** | ✅ IDE autocomplete | ❌ Need documentation |
| **Type Safety** | ✅ Full type hints & enums | ❌ Strings and dicts |
| **Validation** | ✅ Early with clear errors | ❌ Runtime failures |
| **Simplicity** | ✅ Simple things are simple | ❌ Always complex |
| **Power** | ✅ Complex things possible | ❌ Limited capabilities |
| **Maintainability** | ✅ Easy to modify | ❌ Fragile |
| **Testability** | ✅ Components isolated | ❌ Tightly coupled |
| **Documentation** | ✅ Self-documenting code | ❌ Need extensive docs |
| **Learning Curve** | ✅ Gentle, progressive | ❌ Steep |

---

## Design Principles Summary

1. **Use Domain Language**: Match how index professionals think and speak
2. **Make Intent Clear**: No magic, no abbreviations, no jargon
3. **Fail Early**: Validate at build time, not runtime
4. **Be Type-Safe**: Use enums, type hints, strong typing
5. **Progressive Disclosure**: Simple by default, complex when needed
6. **Fluent Interfaces**: Chainable, readable, discoverable
7. **Self-Documenting**: Code explains itself
8. **Composable**: Build complex things from simple parts
9. **Tested & Validated**: Ensure correctness at every step
10. **Production-Ready**: Not just a toy, but enterprise-grade

---

These principles result in an API that is:
- **Intuitive** for index professionals
- **Productive** for daily use
- **Reliable** for production systems
- **Maintainable** for long-term evolution
- **Professional** in quality and polish



