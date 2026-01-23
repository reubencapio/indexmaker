# IndexMaker

A domain-driven Python module for creating, managing, and analyzing financial indices. Designed for index professionals.

[![CI](https://github.com/reubencapio/indexforge/actions/workflows/ci.yml/badge.svg)](https://github.com/reubencapio/indexforge/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/indexforge.svg)](https://badge.fury.io/py/indexforge)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Domain-Driven Design**: API uses terminology familiar to index professionals
- **Fluent Interface**: Chainable methods for intuitive configuration
- **Type-Safe**: Full type hints for IDE support and early error detection
- **Interchangeable Data Sources**: Easily swap between free (Yahoo Finance) and proprietary data
- **Production-Ready**: Includes validation, backtesting, and comprehensive testing

## Installation

### From PyPI

```bash
pip install indexforge
```

### Using Poetry (Development)

```bash
# Clone the repository
git clone https://github.com/reubencapio/indexforge.git
cd indexforge

# Install with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### From Source

```bash
# Install from GitHub
pip install git+https://github.com/reubencapio/indexforge.git
```

## Quick Start

### Create a Simple Index

```python
from indexforge import Index, Universe, WeightingMethod, Currency

# Create an index
index = Index.create(
    name="Tech Leaders Index",
    identifier="TECHLDRS",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)

# Define the universe
universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL", "AMZN", "META"])

# Configure
index.set_universe(universe)
index.set_weighting_method(WeightingMethod.equal_weight())

# Get constituents
constituents = index.get_constituents(date="2025-11-15")
for c in constituents:
    print(f"{c.ticker}: {c.name} - {c.weight:.2%}")
```

### Market Cap Weighted Index with Caps

```python
from indexforge import (
    Index, Universe, SelectionCriteria, WeightingMethod,
    RebalancingSchedule, Currency, Factor
)

# Create the index
index = Index.create(
    name="Tech Leaders Index",
    identifier="TECHLDRS",
    currency=Currency.USD,
    base_date="2025-01-01",
    base_value=1000.0
)

# Define universe with criteria
universe = (Universe.builder()
    .asset_class("EQUITIES")
    .sectors(["Technology"])
    .min_market_cap(1_000_000_000)
    .build()
)

# Select top 50 by market cap
selection = (SelectionCriteria.builder()
    .ranking_by(Factor.MARKET_CAP)
    .select_top(50)
    .apply_buffer_rules(add_threshold=45, remove_threshold=60)
    .build()
)

# Market cap weighting with 10% cap
weighting = (WeightingMethod.market_cap()
    .with_cap(max_weight=0.10)
    .build()
)

# Quarterly rebalancing
rebalancing = RebalancingSchedule.quarterly()

# Configure the index
(index
    .set_universe(universe)
    .set_selection_criteria(selection)
    .set_weighting_method(weighting)
    .set_rebalancing_schedule(rebalancing)
)

# Backtest
result = index.backtest(
    start_date="2024-01-01",
    end_date="2024-12-31"
)
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```

### Using Custom Data Source

```python
from indexmaker import DataConnector, DataProvider, Constituent
import pandas as pd

class MyDataConnector(DataConnector):
    """Your custom data source."""

    def get_prices(self, tickers, start_date, end_date):
        # Fetch from your database/API
        return pd.DataFrame(...)

    def get_constituent_data(self, tickers, as_of_date=None):
        # Return list of Constituent objects
        return [Constituent(ticker=t, ...) for t in tickers]

    def get_market_cap(self, tickers, as_of_date=None):
        return {t: market_cap for t in tickers}

# Use custom data
provider = (DataProvider.builder()
    .add_source("mydata", MyDataConnector())
    .set_default("mydata")
    .build()
)

index.set_data_provider(provider)
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    User API Layer                        │
│   Index.create() → set_universe() → calculate()         │
├──────────────────────────────────────────────────────────┤
│                  Domain Model Layer                      │
│   Index │ Universe │ Constituent │ SelectionCriteria    │
├──────────────────────────────────────────────────────────┤
│                   Strategy Layer                         │
│   WeightingMethod │ RebalancingSchedule │ Validation    │
├──────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│   DataProvider → DataConnector (Yahoo, Custom, etc.)    │
└──────────────────────────────────────────────────────────┘
```

## Core Concepts

### 1. Index
The main entry point. Represents a financial index.

### 2. Universe
Defines which securities are eligible for inclusion (asset class, region, market cap, etc.)

### 3. SelectionCriteria
How constituents are chosen from the universe (top N by factor, composite scoring, etc.)

### 4. WeightingMethod
How constituents are weighted (equal, market cap, factor-based, custom)

### 5. RebalancingSchedule
When the index is updated (quarterly, monthly, annual)

### 6. DataProvider
Abstraction for market data - swap between free and proprietary sources

## Examples

See the `examples/` directory:

- `simple_index.py` - Basic equal-weighted index
- `market_cap_index.py` - Full-featured market cap weighted index
- `custom_data_source.py` - Using your own data source

Run examples:

```bash
poetry run python examples/simple_index.py
poetry run python examples/market_cap_index.py
poetry run python examples/custom_data_source.py
```

## Development

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=indexmaker

# Format code
poetry run black src/ tests/ examples/

# Lint code
poetry run ruff check src/ tests/ examples/

# Type check
poetry run mypy src/indexmaker
```

Or use the Makefile shortcuts:

```bash
make test       # Run tests
make coverage   # Tests with coverage
make format     # Format with Black
make lint       # Run Ruff + Mypy
make all        # Format + Lint + Test
```

## Project Structure

```
indexmaker/
├── src/indexmaker/
│   ├── core/           # Domain models (Index, Universe, Constituent)
│   ├── selection/      # Selection criteria and factors
│   ├── weighting/      # Weighting methods
│   ├── rebalancing/    # Rebalancing schedules
│   ├── data/           # Data providers and connectors
│   └── validation/     # Validation rules
├── tests/              # Unit tests
├── examples/           # Usage examples
└── docs/               # Documentation
```

## Key Design Principles

1. **Domain Language**: API uses industry terminology (constituents, rebalancing, weighting)
2. **Data Source Agnostic**: Core logic separated from data fetching
3. **Type Safety**: Full type hints and validation
4. **Builder Pattern**: Fluent configuration for complex objects
5. **Testability**: Components can be tested in isolation

## Documentation

- [API Design Proposal](API_DESIGN_PROPOSAL.md) - Complete API specification
- [Quick Reference](API_QUICK_REFERENCE.md) - Common patterns cheat sheet
- [Free Data Sources](FREE_DATA_SOURCES.md) - Using Yahoo Finance and other free data
- [Design Rationale](DESIGN_RATIONALE.md) - Why the API is designed this way
- [Module Structure](MODULE_STRUCTURE.md) - Architecture details

## Requirements

- Python 3.9+
- pandas >= 2.0.0
- numpy >= 1.24.0
- yfinance >= 0.2.0 (for free data)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please read the contributing guidelines first.

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

## Acknowledgments

Inspired by industry-standard index methodologies.
