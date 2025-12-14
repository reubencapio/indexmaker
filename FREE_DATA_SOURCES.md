# Free Data Sources for Index Creation

This guide shows free data sources you can use to create indices with the Index Maker module.

## 📊 Available Free Data Sources

### 1. **Yahoo Finance (yfinance)** ⭐ RECOMMENDED
**Best for**: General stock data, easy to use, no API key needed

**What it provides:**
- Historical stock prices (open, high, low, close, adjusted close)
- Trading volume
- Dividends and stock splits
- Market capitalization
- Basic fundamental data
- Global coverage (US, Europe, Asia, etc.)

**Installation:**
```bash
pip install yfinance
```

**Limits:**
- Free, no API key required
- Rate limits exist but generous for personal use
- Historical data available
- Real-time is delayed (15-20 minutes)

---

### 2. **Alpha Vantage**
**Best for**: Time series data, technical indicators

**What it provides:**
- Intraday, daily, weekly, monthly stock data
- Technical indicators
- Forex and crypto data
- Fundamental data (limited free tier)

**Installation:**
```bash
pip install alpha_vantage
```

**Limits:**
- Free API key required (get at alphavantage.co)
- 5 API calls per minute
- 500 calls per day

---

### 3. **Financial Modeling Prep (FMP)**
**Best for**: Financial statements, company profiles, index constituents

**What it provides:**
- Stock prices
- Financial statements
- Company profiles
- Index constituents (S&P 500, etc.)
- Market cap, sector, industry

**Installation:**
```bash
pip install financialmodelingprep
```

**Limits:**
- Free API key required
- 250 calls per day
- Limited historical data on free tier

---

### 4. **Pandas DataReader**
**Best for**: Multiple data sources in one interface

**What it provides:**
- Access to multiple sources (FRED, World Bank, OECD)
- Economic indicators
- Some market data

**Installation:**
```bash
pip install pandas-datareader
```

**Limits:**
- Varies by source
- Some sources require API keys

---

### 5. **OpenBB (formerly Gamestonk Terminal)**
**Best for**: Comprehensive financial data aggregation

**What it provides:**
- Aggregates multiple free data sources
- Stock data, options, crypto, economy
- Alternative data

**Installation:**
```bash
pip install openbb
```

**Limits:**
- Free tier available
- Some features require paid data sources

---

## 🔧 Integration with Index Maker

### Quick Example: Using Yahoo Finance

```python
import yfinance as yf
import pandas as pd
from datetime import datetime
from indexmaker import DataConnector

class YahooFinanceConnector(DataConnector):
    """Free data connector using Yahoo Finance."""
    
    def get_prices(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical prices for given tickers."""
        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            group_by='ticker',
            auto_adjust=True,
            threads=True
        )
        return data
    
    def get_market_cap(self, tickers: list, date: str = None) -> dict:
        """Fetch market capitalization."""
        market_caps = {}
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            info = stock.info
            market_caps[ticker] = info.get('marketCap', 0)
        return market_caps
    
    def get_volume(self, tickers: list, date: str) -> dict:
        """Fetch trading volume."""
        volumes = {}
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=date, end=date)
            if not hist.empty:
                volumes[ticker] = hist['Volume'].iloc[0]
        return volumes
    
    def get_fundamentals(self, ticker: str) -> dict:
        """Fetch fundamental data."""
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'market_cap': info.get('marketCap', 0),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'country': info.get('country', 'Unknown'),
            'currency': info.get('currency', 'USD'),
            'shares_outstanding': info.get('sharesOutstanding', 0),
            'free_float': info.get('floatShares', 0) / info.get('sharesOutstanding', 1) if info.get('sharesOutstanding') else 0
        }
    
    def get_dividends(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch dividend history."""
        stock = yf.Ticker(ticker)
        dividends = stock.dividends
        return dividends[(dividends.index >= start_date) & (dividends.index <= end_date)]
    
    def get_splits(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch stock splits."""
        stock = yf.Ticker(ticker)
        splits = stock.splits
        return splits[(splits.index >= start_date) & (splits.index <= end_date)]
```

### Using the Yahoo Finance Connector

```python
from indexmaker import Index, Universe, DataProvider, WeightingMethod, Currency

# Create the free data connector
yahoo_connector = YahooFinanceConnector()

# Create data provider
data_provider = (DataProvider.builder()
    .add_custom_source("yahoo", yahoo_connector)
    .set_default_source("yahoo")
    .build()
)

# Create your index
index = Index.create(
    name="My Tech Index",
    identifier="MYTECH",
    currency=Currency.USD,
    base_date="2024-01-01",
    base_value=1000.0
)

# Define universe with specific tickers
universe = Universe.from_tickers([
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "NFLX", "ADBE", "CRM"
])

# Configure
index.set_data_provider(data_provider)
index.set_universe(universe)
index.set_weighting_method(WeightingMethod.market_cap().with_cap(0.15).build())

# Calculate!
value = index.calculate(date="2024-11-15")
print(f"Index value: {value}")
```

---

## 📝 Complete Working Example

Here's a full example you can run today with free data:

```python
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Step 1: Define your universe (stocks to consider)
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

# Step 2: Fetch data from Yahoo Finance (FREE!)
print("Fetching data from Yahoo Finance...")
data = yf.download(tickers, start="2024-01-01", end="2024-11-15", group_by='ticker')

# Step 3: Get current market caps
print("\nFetching market caps...")
market_caps = {}
for ticker in tickers:
    stock = yf.Ticker(ticker)
    info = stock.info
    market_caps[ticker] = info.get('marketCap', 0)

# Step 4: Calculate market cap weights
total_market_cap = sum(market_caps.values())
weights = {ticker: cap / total_market_cap for ticker, cap in market_caps.items()}

# Step 5: Apply 15% cap per stock
max_weight = 0.15
for ticker in weights:
    if weights[ticker] > max_weight:
        weights[ticker] = max_weight

# Renormalize
total_weight = sum(weights.values())
weights = {ticker: weight / total_weight for ticker, weight in weights.items()}

# Step 6: Calculate index value
print("\n📊 Index Composition:")
for ticker, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f"  {ticker}: {weight:.2%}")

# Step 7: Calculate index returns
# Get closing prices
closing_prices = pd.DataFrame()
for ticker in tickers:
    if ticker in data.columns.levels[0]:
        closing_prices[ticker] = data[ticker]['Close']

# Calculate weighted returns
weighted_returns = closing_prices.pct_change() * pd.Series(weights)
index_returns = weighted_returns.sum(axis=1)

# Calculate index level (starting at 1000)
index_level = (1 + index_returns).cumprod() * 1000

print(f"\n✅ Final Index Value: {index_level.iloc[-1]:.2f}")
print(f"📈 Total Return: {(index_level.iloc[-1] / 1000 - 1) * 100:.2f}%")

# Plot if matplotlib is available
try:
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=(12, 6))
    index_level.plot()
    plt.title("Index Performance")
    plt.xlabel("Date")
    plt.ylabel("Index Level")
    plt.grid(True)
    plt.savefig("index_performance.png")
    print("\n📊 Chart saved as 'index_performance.png'")
except ImportError:
    print("\nInstall matplotlib to see chart: pip install matplotlib")
```

---

## 🎯 Practical Index Creation with Free Data

### Example 1: Equal-Weighted Tech Index

```python
import yfinance as yf
import pandas as pd

# Define universe
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

# Fetch 1 year of data
data = yf.download(tickers, period="1y")

# Equal weight = 1/n
weight = 1.0 / len(tickers)

# Calculate index
closing_prices = data['Close']
returns = closing_prices.pct_change()
index_returns = returns.mean(axis=1)  # Equal weight
index_level = (1 + index_returns).cumprod() * 1000

print(f"Index value: {index_level.iloc[-1]:.2f}")
```

### Example 2: Market Cap Weighted Index

```python
import yfinance as yf

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

# Get market caps
market_caps = {}
for ticker in tickers:
    stock = yf.Ticker(ticker)
    market_caps[ticker] = stock.info['marketCap']

# Calculate weights
total_cap = sum(market_caps.values())
weights = {t: mc / total_cap for t, mc in market_caps.items()}

print("Market Cap Weights:")
for ticker, weight in weights.items():
    print(f"  {ticker}: {weight:.2%}")
```

### Example 3: Dividend Yield Weighted Index

```python
import yfinance as yf

tickers = ["AAPL", "MSFT", "JPM", "JNJ", "PG"]

# Get dividend yields
dividend_yields = {}
for ticker in tickers:
    stock = yf.Ticker(ticker)
    info = stock.info
    dividend_yields[ticker] = info.get('dividendYield', 0)

# Calculate weights based on dividend yield
total_yield = sum(dividend_yields.values())
weights = {t: dy / total_yield for t, dy in dividend_yields.items()}

print("Dividend Yield Weights:")
for ticker, weight in weights.items():
    print(f"  {ticker}: {weight:.2%}")
```

---

## 🔍 Data Coverage Comparison

| Data Source | Stocks | Market Cap | Volume | Fundamentals | Dividends | Splits | API Key |
|------------|--------|------------|--------|--------------|-----------|--------|---------|
| **Yahoo Finance** | ✅ Global | ✅ Yes | ✅ Yes | ✅ Basic | ✅ Yes | ✅ Yes | ❌ No |
| **Alpha Vantage** | ✅ US mainly | ❌ Limited | ✅ Yes | ✅ Limited | ❌ No | ❌ No | ✅ Yes |
| **FMP** | ✅ US mainly | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Pandas DataReader** | ⚠️ Varies | ⚠️ Varies | ⚠️ Varies | ❌ No | ❌ No | ❌ No | ⚠️ Depends |

**Recommendation**: Start with **Yahoo Finance (yfinance)** - it's free, requires no API key, and covers most use cases.

---

## ⚠️ Limitations of Free Data

### What Free Data Can Do:
✅ Create proof-of-concept indices
✅ Backtest strategies
✅ Educational and research purposes
✅ Personal portfolio tracking
✅ Basic fundamental screening

### What You Need Paid Data For:
❌ Production-grade indices for clients
❌ Real-time data (free data is delayed 15-20 min)
❌ Comprehensive fundamental data
❌ Corporate actions with exact timing
❌ ESG scores and alternative data
❌ Tick-by-tick data
❌ Official exchange data quality

---

## 🚀 Getting Started Checklist

1. **Install yfinance**
   ```bash
   pip install yfinance pandas numpy
   ```

2. **Test data fetch**
   ```python
   import yfinance as yf
   stock = yf.Ticker("AAPL")
   print(stock.info['marketCap'])
   ```

3. **Create simple index** (use example above)

4. **Integrate with Index Maker** (use connector pattern)

5. **Backtest your strategy**

6. **Validate results** (compare with known indices)

7. **When ready for production**: Consider paid data sources
   - Bloomberg
   - Refinitiv
   - FactSet
   - Morningstar

---

## 💡 Pro Tips

### Tip 1: Cache Data Locally
```python
# Download once, use many times
data = yf.download(tickers, start="2020-01-01", end="2024-12-31")
data.to_csv("historical_data.csv")

# Later, load from file
data = pd.read_csv("historical_data.csv", index_col=0, parse_dates=True)
```

### Tip 2: Handle Missing Data
```python
# Yahoo Finance sometimes has gaps
data = data.fillna(method='ffill')  # Forward fill
data = data.dropna()  # Or drop rows with missing data
```

### Tip 3: Batch Requests
```python
# Faster: Download all at once
data = yf.download(["AAPL", "MSFT", "GOOGL"], period="1y")

# Slower: One by one
for ticker in tickers:
    data = yf.download(ticker, period="1y")
```

### Tip 4: Error Handling
```python
import yfinance as yf

def safe_fetch_market_cap(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.info.get('marketCap', 0)
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return 0
```

### Tip 5: Rate Limiting for Alpha Vantage
```python
import time
from alpha_vantage.timeseries import TimeSeries

ts = TimeSeries(key='YOUR_API_KEY')

for ticker in tickers:
    data, meta = ts.get_daily(ticker)
    time.sleep(12)  # 5 calls per minute = 12 seconds between calls
```

---

## 📚 Additional Resources

### Libraries Documentation:
- **yfinance**: https://github.com/ranaroussi/yfinance
- **Alpha Vantage**: https://www.alphavantage.co/documentation/
- **FMP**: https://site.financialmodelingprep.com/developer/docs
- **Pandas DataReader**: https://pandas-datareader.readthedocs.io/

### Tutorials:
- Building indices with Python: https://www.quantstart.com/
- Financial data analysis: https://www.datacamp.com/

### Communities:
- r/algotrading
- QuantConnect forums
- StackOverflow [yfinance] tag

---

## 🎓 Next Steps

1. **Start with the working example** in this document
2. **Modify it** for your specific universe
3. **Integrate with Index Maker API** using the connector pattern
4. **Backtest thoroughly** with historical data
5. **Validate against known indices** (e.g., compare with S&P 500)
6. **Document your methodology**
7. **When ready for production**, consider upgrading to professional data sources

---

**Remember**: Free data is perfect for learning, prototyping, and personal use. For production indices that clients will rely on, invest in professional-grade data sources.

**Start building your first index now!** All the tools you need are free and available today. 🚀



