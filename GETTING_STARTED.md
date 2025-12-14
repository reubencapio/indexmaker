# Getting Started with Index Maker

A quick tutorial to get you creating indices in minutes.

## Installation (Future)

```bash
pip install index-maker
```

---

## 5-Minute Quick Start

### Step 1: Import and Create Your First Index

```python
from indexmaker import Index, Currency

index = Index.create(
    name="My First Index",
    identifier="MYFIRST",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)
```

✅ **You now have an index!** Let's add some stocks.

---

### Step 2: Define What Goes Into Your Index (Universe)

```python
from indexmaker import Universe

# Option 1: Start with specific tickers
universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL", "AMZN", "META"])
index.set_universe(universe)

# Option 2: Define broader criteria
universe = (Universe.builder()
    .asset_class("EQUITIES")
    .sectors(["Technology"])
    .min_market_cap(10_000_000_000)  # $10B minimum
    .build()
)
index.set_universe(universe)
```

✅ **Your index knows which stocks it can include!**

---

### Step 3: How to Weight the Stocks

```python
from indexmaker import WeightingMethod

# Equal weight - simplest approach
weighting = WeightingMethod.equal_weight()
index.set_weighting_method(weighting)

# Or market cap weighted with a cap
weighting = (WeightingMethod.market_cap()
    .with_cap(max_weight=0.15)  # No stock more than 15%
    .build()
)
index.set_weighting_method(weighting)
```

✅ **Your index knows how to distribute weight!**

---

### Step 4: Calculate Your Index

```python
# Calculate current value
value = index.calculate(date="2025-11-15")
print(f"Index value: {value}")

# See what's inside
constituents = index.get_constituents(date="2025-11-15")
for c in constituents:
    print(f"{c.name}: {c.weight:.2%}")
```

✅ **You've calculated your first index!**

---

## Complete Example - Copy and Run

```python
from indexmaker import Index, Universe, WeightingMethod, Currency

# 1. Create the index
index = Index.create(
    name="Tech Giants Index",
    identifier="TECHGNT",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)

# 2. Define universe (what CAN be in the index)
universe = Universe.from_tickers([
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "NFLX", "ADBE", "CRM"
])

# 3. Set equal weighting
weighting = WeightingMethod.equal_weight()

# 4. Configure the index
index.set_universe(universe)
index.set_weighting_method(weighting)

# 5. Calculate!
value = index.calculate(date="2025-11-15")
print(f"✅ Index value: {value}")

# 6. See constituents
constituents = index.get_constituents(date="2025-11-15")
print(f"\n📊 Constituents:")
for c in constituents:
    print(f"  {c.ticker:6s} {c.name:30s} {c.weight:6.2%}")
```

---

## Next Level: Professional Index

Let's create a more sophisticated index with selection criteria and rebalancing.

```python
from indexmaker import (
    Index, Universe, SelectionCriteria, WeightingMethod, 
    RebalancingSchedule, Factor, Currency
)

# Create index
index = Index.create(
    name="Top 50 Tech Index",
    identifier="TECH50",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)

# Define universe - tech stocks with minimum requirements
universe = (Universe.builder()
    .asset_class("EQUITIES")
    .sectors(["Technology", "Communication Services"])
    .min_market_cap(1_000_000_000)      # $1B minimum
    .min_average_daily_volume(1_000_000) # $1M daily volume
    .min_free_float(0.15)                # 15% free float
    .build()
)

# Select top 50 by market cap with buffer rules
selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .apply_buffer_rules(
        add_threshold=45,    # Add if ranked 45 or better
        remove_threshold=60  # Remove if ranked worse than 60
    )
    .build()
)

# Market cap weighting with 10% cap per stock
weighting = (WeightingMethod.market_cap()
    .with_cap(max_weight=0.10)
    .build()
)

# Rebalance quarterly
rebalancing = RebalancingSchedule.quarterly()

# Configure everything
(index
    .set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
    .set_rebalancing_schedule(rebalancing)
)

# Calculate
value = index.calculate(date="2025-11-15")
print(f"Index value: {value}")

# Get performance metrics
performance = index.get_performance(
    start_date="2025-01-01",
    end_date="2025-11-15"
)
print(f"YTD Return: {performance.total_return:.2%}")
print(f"Volatility: {performance.volatility:.2%}")
```

---

## Understanding the Building Blocks

### 1. **Index** - The Container
The main object that holds everything together.

```python
index = Index.create(name="...", identifier="...", ...)
```

### 2. **Universe** - The Pool of Possibilities
Defines which securities *can* be in the index.

```python
universe = Universe.builder()...
```

Think of it as: "These are ALL the stocks we're considering"

### 3. **SelectionCriteria** - The Filter
Determines which securities from the universe are *actually* selected.

```python
selection = SelectionCriteria.builder().select_top(50)...
```

Think of it as: "From the universe, pick THESE specific ones"

### 4. **WeightingMethod** - The Distribution
Determines how much of each selected security to hold.

```python
weighting = WeightingMethod.market_cap()...
```

Think of it as: "How much of each should we hold?"

### 5. **RebalancingSchedule** - The Update Cadence
Determines when to refresh the selection and weights.

```python
rebalancing = RebalancingSchedule.quarterly()
```

Think of it as: "When do we update?"

---

## Common Patterns

### Pattern 1: Simple Static Index
**Use Case**: Fixed list of stocks, rarely changes

```python
index = Index.create(...)
index.set_universe(Universe.from_tickers(["AAPL", "MSFT", "GOOGL"]))
index.set_weighting_method(WeightingMethod.equal_weight())
```

### Pattern 2: Top N by Market Cap
**Use Case**: Largest companies in a sector

```python
universe = Universe.builder().sectors(["Technology"]).build()
selection = SelectionCriteria.top_by_market_cap(50)
weighting = WeightingMethod.market_cap().with_cap(0.10).build()
```

### Pattern 3: Multi-Factor Strategy
**Use Case**: Combine different factors

```python
from indexmaker import CompositeScore, Factor

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

### Pattern 4: ESG-Screened Index
**Use Case**: Sustainable investing

```python
universe = (Universe.builder()
    .asset_class("EQUITIES")
    .esg_screening(
        min_esg_score=70,
        exclude_controversial_weapons=True,
        exclude_tobacco=True
    )
    .build()
)
```

---

## Testing Your Index: Backtesting

Before going live, test your index on historical data:

```python
# Backtest from 2020 to 2024
backtest = index.backtest(
    start_date="2020-01-01",
    end_date="2024-12-31",
    initial_value=1000.0
)

# View results
print(f"Annualized Return: {backtest.annualized_return:.2%}")
print(f"Volatility: {backtest.volatility:.2%}")
print(f"Sharpe Ratio: {backtest.sharpe_ratio:.2f}")
print(f"Max Drawdown: {backtest.max_drawdown:.2%}")

# Compare with benchmark
comparison = backtest.compare_with_benchmark("SPX")
print(f"Alpha vs S&P 500: {comparison.alpha:.2%}")
print(f"Beta: {comparison.beta:.2f}")
```

---

## Generating Documentation

Automatically create professional documents:

```python
from indexmaker import DocumentGenerator

# Generate index guideline
DocumentGenerator.for_index(index).generate("GUIDELINE").save_to("guideline.pdf")

# Generate factsheet
DocumentGenerator.for_index(index).generate("FACTSHEET").save_to("factsheet.pdf")

# Generate methodology document
DocumentGenerator.for_index(index).generate("METHODOLOGY").save_to("methodology.pdf")
```

---

## Saving and Loading

Save your index configuration for reuse:

```python
# Save
index.save("my_index_config.json")

# Later, load it back
index = Index.load("my_index_config.json")

# Make modifications
index.set_weighting_method(new_weighting)
index.save("my_index_config_v2.json")
```

---

## Common Questions

### Q: Can I use custom data sources?
**A:** Yes! Implement a custom DataConnector.

```python
class MyDataSource(DataConnector):
    def get_prices(self, tickers, date):
        # Your logic here
        pass

data_provider = DataProvider.builder().add_custom_source("my_data", MyDataSource()).build()
index.set_data_provider(data_provider)
```

### Q: Can I add custom selection logic?
**A:** Yes! Use custom rules.

```python
@CustomRule.selection
def my_filter(context):
    # Your logic
    return True  # Include or False to exclude

selection = SelectionCriteria.builder().custom_filter(my_filter).build()
```

### Q: How do I handle corporate actions?
**A:** Configure a corporate actions policy.

```python
from indexmaker import CorporateActions

ca_policy = (CorporateActions.builder()
    .on_dividend(action="reinvest")
    .on_split(action="adjust_price_and_shares")
    .on_merger(action="replace_with_acquirer")
    .build()
)
index.set_corporate_actions_policy(ca_policy)
```

### Q: Can I create index variants (e.g., total return)?
**A:** Yes!

```python
# Create total return variant
tr_index = index.create_variant(
    variant_type=IndexType.TOTAL_RETURN,
    identifier="MYIDXTR"
)

# Create currency-hedged variant
hedged = index.create_variant(
    variant_type=IndexType.CURRENCY_HEDGED,
    target_currency=Currency.EUR
)
```

---

## What's Next?

1. **Try [Free Data Sources](FREE_DATA_SOURCES.md)** to start building with real data today! ⭐
2. **Read the [Quick Reference](API_QUICK_REFERENCE.md)** for common code patterns
3. **Explore the [Complete API](API_DESIGN_PROPOSAL.md)** for all features
4. **Understand [Design Decisions](DESIGN_RATIONALE.md)** for best practices
5. **Check [Module Structure](MODULE_STRUCTURE.md)** for architecture details

---

## Getting Help

### Documentation
- **Quick Reference**: Common patterns and examples
- **API Design Proposal**: Complete feature documentation
- **Design Rationale**: Why the API is designed this way
- **Module Structure**: Architecture and implementation details

### Code Examples
Look at the examples in each documentation file - they're all runnable!

### Best Practices
1. **Start simple**: Begin with basic examples
2. **Validate early**: Use `index.validate()` to catch errors
3. **Backtest thoroughly**: Test before production
4. **Use type hints**: Better IDE support
5. **Save configurations**: Version control your indices

---

## Your First Task

Try this 5-minute exercise:

1. Create an index with 3-5 stocks you know
2. Use equal weighting
3. Calculate the index value
4. Print the constituents
5. Save the configuration

```python
from indexmaker import Index, Universe, WeightingMethod, Currency

# Your code here!
index = Index.create(
    name="My Test Index",
    identifier="MYTEST",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)

# Add your stocks
universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL"])

# Configure and calculate
index.set_universe(universe)
index.set_weighting_method(WeightingMethod.equal_weight())

value = index.calculate(date="2025-11-15")
print(f"Success! Index value: {value}")

# Save it
index.save("my_first_index.json")
```

**Congratulations!** You've created your first index. 🎉

---

## Tips for Success

✅ **Do:**
- Start with simple examples and add complexity gradually
- Use the builder pattern for complex configurations
- Validate your configuration before calculating
- Backtest before going to production
- Use type hints for better IDE support

❌ **Don't:**
- Try to configure everything at once
- Skip validation
- Go to production without backtesting
- Ignore error messages (they're helpful!)
- Use magic numbers (use named parameters)

---

**Ready to build professional indices?** Start with the examples above and explore the full API documentation when you need more advanced features.

