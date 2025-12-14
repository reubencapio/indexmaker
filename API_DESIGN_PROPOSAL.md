# Index Maker - API Design Proposal

## Overview

This document outlines a domain-driven Python API for creating and managing indices. The API is designed to match the mental model of index professionals and align with standard industry terminology.

## Design Principles

1. **Domain-Driven Language**: Uses terminology from the index industry (constituents, rebalancing, methodology, etc.)
2. **Fluent Interface**: Chainable methods for intuitive configuration
3. **Declarative Configuration**: Express intent clearly without implementation details
4. **Type Safety**: Leverage Python type hints for better IDE support
5. **Validation**: Early validation with clear error messages
6. **Flexibility**: Support multiple methodologies and customization

---

## Core API Design

### 1. Index Creation and Basic Configuration

```python
from indexmaker import Index, IndexType, Currency

# Create a new index
index = Index.create(
    name="Global Tech Leaders Index",
    identifier="TECHLDRS",
    isin="DE000SL0ABC1",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0,
    index_type=IndexType.PRICE_RETURN
)
```

**Key Features:**
- Clear factory method pattern
- Required parameters are explicit
- Strongly typed enums for standard values
- Immutable after creation (use builder for modifications)

---

### 2. Defining the Index Universe

```python
from indexmaker import Universe, AssetClass, Region, ExchangeList

# Define the investment universe
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .regions([Region.NORTH_AMERICA, Region.EUROPE])
    .exchanges(ExchangeList.PRIMARY_EXCHANGES)
    .sectors(["Technology", "Communication Services"])
    .build()
)

index.set_universe(universe)
```

**Alternative Approach - More Specific:**

```python
# For more granular control
universe = (Universe.builder()
    .include_countries(["US", "DE", "FR", "GB"])
    .exclude_countries(["RU"])
    .exchanges(["NYSE", "NASDAQ", "XETRA", "LSE"])
    .min_market_cap(500_000_000, currency=Currency.USD)
    .min_average_daily_volume(1_000_000, currency=Currency.USD)
    .min_free_float(0.15)
    .build()
)
```

---

### 3. Selection Criteria

```python
from indexmaker import SelectionCriteria, RankingMethod, Factor

# Define how constituents are selected
selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .apply_buffer_rules(
        add_threshold=45,  # Add if ranked 45 or better
        remove_threshold=60  # Remove if ranked worse than 60
    )
    .build()
)

index.set_selection_criteria(selection)
```

**Advanced Selection - Multi-Factor:**

```python
from indexmaker import CompositeScore, Factor

# Combine multiple factors
selection = (SelectionCriteria.builder()
    .composite_score(
        CompositeScore.builder()
            .add_factor(Factor.MARKET_CAP, weight=0.4)
            .add_factor(Factor.LIQUIDITY, weight=0.3)
            .add_factor(Factor.MOMENTUM, weight=0.3)
            .build()
    )
    .select_top(100)
    .filter_by_ratio(
        numerator="revenue",
        denominator="market_cap",
        percentile_range=(10, 90)  # Select middle 80%
    )
    .build()
)
```

---

### 4. Weighting Methodology

```python
from indexmaker import WeightingMethod, CapFactor

# Simple equal weighting
weighting = WeightingMethod.equal_weight()

# Market cap weighting with caps
weighting = (WeightingMethod.market_cap()
    .with_cap(max_weight=0.10)  # 10% max per constituent
    .with_cap(max_weight_per_issuer=0.15)  # 15% max per issuer
    .build()
)

# Free-float adjusted market cap
weighting = WeightingMethod.free_float_market_cap()

# Custom factor-based weighting
weighting = (WeightingMethod.factor_based()
    .factor(Factor.DIVIDEND_YIELD)
    .with_cap(max_weight=0.08)
    .build()
)

index.set_weighting_method(weighting)
```

---

### 5. Rebalancing and Review Schedule

```python
from indexmaker import RebalancingSchedule, ReviewType

# Quarterly rebalancing
rebalancing = (RebalancingSchedule.builder()
    .frequency("quarterly")
    .on_months([3, 6, 9, 12])
    .on_day(15)  # 15th of the month
    .selection_date_offset(-5)  # 5 business days before
    .announcement_date_offset(-2)  # Announce 2 days before
    .build()
)

index.set_rebalancing_schedule(rebalancing)
```

**Advanced Rebalancing:**

```python
# Different schedules for different actions
rebalancing = (RebalancingSchedule.builder()
    .ordinary_rebalancing(
        frequency="quarterly",
        months=[3, 6, 9, 12],
        day=15
    )
    .constituent_review(
        frequency="monthly",
        review_type=ReviewType.EXTRAORDINARY,
        conditions=["bankruptcy", "merger", "delisting"]
    )
    .weight_adjustment(
        frequency="monthly",
        max_weight_drift=0.05  # Rebalance if weight drifts >5%
    )
    .build()
)
```

---

### 6. Corporate Actions Handling

```python
from indexmaker import CorporateActions

# Define corporate action policies
ca_policy = (CorporateActions.builder()
    .on_dividend(action="reinvest")  # For total return index
    .on_split(action="adjust_price_and_shares")
    .on_merger(action="replace_with_acquirer")
    .on_bankruptcy(action="remove_immediately")
    .on_spin_off(
        action="add_to_index",
        min_market_cap=100_000_000
    )
    .build()
)

index.set_corporate_actions_policy(ca_policy)
```

---

### 7. Calculation Methodology

```python
from indexmaker import CalculationMethod, DivisorAdjustment

# Set calculation parameters
calculation = (CalculationMethod.builder()
    .divisor_adjustment(DivisorAdjustment.CHAIN_LINKED)
    .include_total_return_variant(True)
    .include_net_return_variant(True, withholding_tax_rate=0.15)
    .price_source("official_closing_prices")
    .currency_conversion_rate_source("WM/Reuters")
    .rounding_precision(2)
    .build()
)

index.set_calculation_method(calculation)
```

---

### 8. Index Calculation and Data Access

```python
from datetime import date

# Calculate index value for a specific date
index_value = index.calculate(date="2025-11-15")
print(f"Index value: {index_value}")

# Get constituent details
constituents = index.get_constituents(date="2025-11-15")
for constituent in constituents:
    print(f"{constituent.name}: {constituent.weight:.2%}, Shares: {constituent.shares}")

# Historical performance
performance = index.get_performance(
    start_date="2025-01-01",
    end_date="2025-11-15"
)
print(f"YTD Return: {performance.total_return:.2%}")

# Time series data
timeseries = index.get_timeseries(
    start_date="2025-01-01",
    end_date="2025-11-15",
    frequency="daily"
)
```

---

### 9. Data Integration

```python
from indexmaker import DataProvider, MarketDataSource

# Connect to data sources
data_provider = (DataProvider.builder()
    .market_data(MarketDataSource.BLOOMBERG)
    .corporate_actions(MarketDataSource.REFINITIV)
    .fundamentals(MarketDataSource.FACTSET)
    .add_custom_source(
        name="internal_research",
        connector=my_custom_connector
    )
    .build()
)

index.set_data_provider(data_provider)

# Or use a pre-configured standard data setup
index.use_standard_data_sources()
```

---

### 10. Validation and Compliance

```python
from indexmaker import ValidationRules, ComplianceCheck

# Set validation rules
validation = (ValidationRules.builder()
    .min_constituents(20)
    .max_constituents(100)
    .min_index_market_cap(1_000_000_000)
    .max_single_constituent_weight(0.15)
    .max_single_country_weight(0.50)
    .require_minimum_turnover(0.05)  # Flag if turnover < 5%
    .build()
)

index.set_validation_rules(validation)

# Run compliance checks
compliance_report = index.run_compliance_check(
    checks=[
        ComplianceCheck.UCITS_COMPLIANT,
        ComplianceCheck.ESG_STANDARDS,
        ComplianceCheck.IOSCO_PRINCIPLES
    ],
    date="2025-11-15"
)

if not compliance_report.is_compliant:
    for issue in compliance_report.issues:
        print(f"Issue: {issue.description}, Severity: {issue.severity}")
```

---

### 11. Backtesting and Simulation

```python
# Backtest the index
backtest = index.backtest(
    start_date="2020-01-01",
    end_date="2024-12-31",
    initial_value=1000.0
)

# Get backtest results
print(f"Annualized Return: {backtest.annualized_return:.2%}")
print(f"Volatility: {backtest.volatility:.2%}")
print(f"Sharpe Ratio: {backtest.sharpe_ratio:.2f}")
print(f"Max Drawdown: {backtest.max_drawdown:.2%}")

# Compare with benchmark
comparison = backtest.compare_with_benchmark("SPX")
print(f"Alpha: {comparison.alpha:.2%}")
print(f"Beta: {comparison.beta:.2f}")
print(f"Tracking Error: {comparison.tracking_error:.2%}")
```

**Simulation for Index Modifications:**

```python
# Simulate what-if scenarios
simulation = index.simulate(
    modification=lambda idx: idx.set_weighting_method(
        WeightingMethod.equal_weight()
    ),
    start_date="2020-01-01",
    end_date="2024-12-31"
)

# Compare with current methodology
comparison = simulation.compare_with_original()
print(f"Return Difference: {comparison.return_diff:.2%}")
print(f"Turnover Increase: {comparison.turnover_diff:.2%}")
```

---

### 12. Documentation Generation

```python
from indexmaker import DocumentGenerator, DocumentType

# Generate index guideline
guideline = (DocumentGenerator
    .for_index(index)
    .generate(DocumentType.GUIDELINE)
    .with_branding("MyCompany")
    .with_template("standard")
    .save_to("guideline.pdf")
)

# Generate factsheet
factsheet = (DocumentGenerator
    .for_index(index)
    .generate(DocumentType.FACTSHEET)
    .with_data_as_of("2025-11-15")
    .with_performance_chart(years=5)
    .save_to("factsheet.pdf")
)

# Generate methodology document
methodology = (DocumentGenerator
    .for_index(index)
    .generate(DocumentType.METHODOLOGY)
    .include_sections([
        "universe_definition",
        "selection_criteria",
        "weighting_methodology",
        "rebalancing_rules",
        "calculation_formula"
    ])
    .save_to("methodology.pdf")
)
```

---

### 13. Index Variants and Sub-Indices

```python
# Create a total return variant
tr_index = index.create_variant(
    variant_type=IndexType.TOTAL_RETURN,
    identifier="TECHLDRS_TR",
    isin="DE000SL0ABC2"
)

# Create a hedged currency variant
hedged_index = index.create_variant(
    variant_type=IndexType.CURRENCY_HEDGED,
    target_currency=Currency.EUR,
    identifier="TECHLDRS_EH",
    isin="DE000SL0ABC3"
)

# Create a sub-index (e.g., by region)
us_subindex = (index.create_subindex(
    name="US Tech Leaders Index",
    identifier="TECHLDRS_US")
    .filter_constituents(lambda c: c.country == "US")
    .build()
)
```

---

### 14. Publishing and Distribution

```python
from indexmaker import Publisher, DataFormat

# Publish index data
publisher = (Publisher.for_index(index)
    .to_bloomberg(
        ticker="TECHLDRS",
        update_frequency="real-time"
    )
    .to_refinitiv(
        ric="TECHLDRS.IDX"
    )
    .to_website(
        url="https://www.mycompany.com/indices/TECHLDRS",
        format=DataFormat.JSON
    )
    .to_api(
        endpoint="/api/v1/indices/TECHLDRS",
        authentication="api_key"
    )
    .build()
)

# Schedule publication
publisher.schedule(
    frequency="daily",
    time="18:00 CET",
    include_constituents=True,
    include_weights=True
)
```

---

### 15. Comprehensive Example - Putting It All Together

```python
from indexmaker import (
    Index, IndexType, Currency, Universe, AssetClass, Region,
    SelectionCriteria, Factor, WeightingMethod, RebalancingSchedule,
    CorporateActions, CalculationMethod, ValidationRules
)

# Create the index
index = Index.create(
    name="Global Sustainable Tech Index",
    identifier="SOLGSTECH",
    isin="DE000SL0XYZ1",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0,
    index_type=IndexType.TOTAL_RETURN
)

# Define universe
universe = (Universe.builder()
    .asset_class(AssetClass.EQUITIES)
    .regions([Region.GLOBAL])
    .sectors(["Technology", "Communication Services"])
    .min_market_cap(1_000_000_000, currency=Currency.USD)
    .min_average_daily_volume(2_000_000, currency=Currency.USD)
    .min_free_float(0.20)
    .esg_screening(
        min_esg_score=70,
        exclude_controversial_weapons=True,
        exclude_tobacco=True
    )
    .build()
)

# Selection criteria - top 50 by market cap
selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .apply_buffer_rules(add_threshold=45, remove_threshold=60)
    .diversification_constraint(
        max_constituents_per_country=15,
        max_constituents_per_sector=20
    )
    .build()
)

# Free-float market cap weighting with caps
weighting = (WeightingMethod.free_float_market_cap()
    .with_cap(max_weight=0.08)
    .with_cap(max_weight_per_issuer=0.10)
    .build()
)

# Quarterly rebalancing
rebalancing = (RebalancingSchedule.builder()
    .frequency("quarterly")
    .on_months([3, 6, 9, 12])
    .on_day(20)
    .selection_date_offset(-10)
    .announcement_date_offset(-5)
    .build()
)

# Corporate actions
ca_policy = (CorporateActions.builder()
    .on_dividend(action="reinvest")
    .on_split(action="adjust_price_and_shares")
    .on_merger(action="follow_index_committee_decision")
    .on_bankruptcy(action="remove_immediately")
    .build()
)

# Calculation method
calculation = (CalculationMethod.builder()
    .divisor_adjustment("chain_linked")
    .include_total_return_variant(True)
    .include_net_return_variant(True, withholding_tax_rate=0.15)
    .price_source("official_closing_prices")
    .build()
)

# Validation rules
validation = (ValidationRules.builder()
    .min_constituents(30)
    .max_constituents(50)
    .max_single_constituent_weight(0.10)
    .max_single_country_weight(0.40)
    .build()
)

# Configure the index
(index
    .set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
    .set_rebalancing_schedule(rebalancing)
    .set_corporate_actions_policy(ca_policy)
    .set_calculation_method(calculation)
    .set_validation_rules(validation)
)

# Use standard data sources
index.use_standard_data_sources()

# Validate the configuration
validation_report = index.validate()
if validation_report.is_valid:
    print("Index configuration is valid!")
else:
    for error in validation_report.errors:
        print(f"Error: {error}")

# Backtest the index
backtest = index.backtest(
    start_date="2020-01-01",
    end_date="2024-12-31",
    initial_value=1000.0
)

print(f"Backtested Performance:")
print(f"  Annualized Return: {backtest.annualized_return:.2%}")
print(f"  Volatility: {backtest.volatility:.2%}")
print(f"  Sharpe Ratio: {backtest.sharpe_ratio:.2f}")

# Generate guideline
(DocumentGenerator
    .for_index(index)
    .generate("GUIDELINE")
    .save_to("global-sustainable-tech-guideline.pdf")
)

# Save index configuration
index.save("global-sustainable-tech-index.json")

# Later, load the index
# loaded_index = Index.load("global-sustainable-tech-index.json")
```

---

## Advanced Features

### 16. Custom Rules and Logic

```python
from indexmaker import CustomRule, RuleContext

# Define custom selection rule
@CustomRule.selection
def tech_innovation_score(context: RuleContext) -> float:
    """Calculate custom tech innovation score."""
    constituent = context.constituent
    rd_spending = constituent.get_fundamental("r_and_d_spending")
    revenue = constituent.get_fundamental("revenue")
    patent_count = constituent.get_custom_data("patent_count")
    
    innovation_score = (
        (rd_spending / revenue) * 0.6 +
        (patent_count / 100) * 0.4
    )
    return innovation_score

# Use in selection
selection = (SelectionCriteria.builder()
    .custom_ranking(tech_innovation_score)
    .select_top(50)
    .build()
)
```

### 17. Event-Driven Updates

```python
from indexmaker import EventListener, IndexEvent

# Set up event listeners
@index.on(IndexEvent.CONSTITUENT_ADDED)
def on_constituent_added(event):
    print(f"Added: {event.constituent.name} on {event.date}")
    # Send notification, update database, etc.

@index.on(IndexEvent.REBALANCING_COMPLETED)
def on_rebalancing(event):
    print(f"Rebalancing completed on {event.date}")
    print(f"Turnover: {event.turnover:.2%}")
    # Generate reports, send alerts, etc.

@index.on(IndexEvent.VALIDATION_FAILED)
def on_validation_failed(event):
    print(f"Validation failed: {event.errors}")
    # Alert index managers

# Trigger calculations with events
index.calculate_with_events(date="2025-11-15")
```

### 18. Multi-Index Management

```python
from indexmaker import IndexFamily

# Create an index family
family = IndexFamily.create(
    name="Tech Benchmark Series",
    base_universe=universe
)

# Add indices to the family
family.add_index(
    name="Large Cap Tech",
    market_cap_range=(10_000_000_000, float('inf'))
)

family.add_index(
    name="Mid Cap Tech",
    market_cap_range=(2_000_000_000, 10_000_000_000)
)

family.add_index(
    name="Small Cap Tech",
    market_cap_range=(300_000_000, 2_000_000_000)
)

# Apply common rules to all indices
family.apply_to_all(
    rebalancing=quarterly_schedule,
    weighting=market_cap_weighting
)

# Calculate all indices
family.calculate_all(date="2025-11-15")

# Compare performance
comparison = family.compare_performance(
    start_date="2025-01-01",
    end_date="2025-11-15"
)
```

---

## Key Benefits of This API Design

### For Users:
1. **Intuitive**: Matches how index professionals think about indices
2. **Self-Documenting**: Method and parameter names clearly express intent
3. **Type-Safe**: IDE autocomplete and type checking catch errors early
4. **Flexible**: Can be simple or complex based on needs
5. **Chainable**: Fluent interface feels natural
6. **Validated**: Early validation with clear error messages

### For Development:
1. **Maintainable**: Clear separation of concerns
2. **Testable**: Each component can be tested independently
3. **Extensible**: Easy to add new features
4. **Consistent**: Follows established patterns throughout

---

## Example Use Cases

### Use Case 1: Quick Prototype
```python
# Create a simple equal-weighted index in 10 lines
index = (Index.create("Test Index", "TEST", Currency.USD, "2025-01-01", 1000)
    .set_universe(Universe.from_tickers(["AAPL", "MSFT", "GOOGL", "AMZN"]))
    .set_weighting_method(WeightingMethod.equal_weight())
    .set_rebalancing_schedule(RebalancingSchedule.quarterly())
)

print(index.calculate(date="2025-11-15"))
```

### Use Case 2: Complex Strategy Index
```python
# Multi-factor, ESG-screened, capped index with custom rules
index = Index.create(...).set_universe(
    Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .esg_screening(min_score=70)
        .exclude_sectors(["Weapons", "Tobacco"])
        .custom_filter(my_proprietary_filter)
        .build()
).set_selection_criteria(
    SelectionCriteria.composite_score()
        .add_factor(Factor.VALUE, 0.3)
        .add_factor(Factor.QUALITY, 0.3)
        .add_factor(Factor.LOW_VOLATILITY, 0.4)
        .select_top(100)
        .build()
)...
```

### Use Case 3: Index Family Management
```python
# Manage multiple related indices efficiently
family = IndexFamily.create("Regional Tech Series")
for region in [Region.US, Region.EUROPE, Region.ASIA]:
    family.add_index(
        name=f"Tech Leaders {region.name}",
        universe=Universe.builder().regions([region]).build()
    )
family.calculate_all_and_publish()
```

---

## Summary

This API design provides:
- **Domain alignment**: Uses industry-standard terminology
- **Excellent UX**: Intuitive, discoverable, self-documenting
- **Flexibility**: Simple for basic use, powerful for advanced needs
- **Type safety**: Leverages Python type hints
- **Validation**: Catch errors early
- **Production-ready**: Includes testing, documentation, publishing

The API reads like a conversation with an index professional, making it easy to express index methodology in code.



