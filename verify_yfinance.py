import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)

tickers = ["NOV.SW", "HSBC.L", "ALL.DE"]

for ticker in tickers:
    try:
        print(f"Fetching info for {ticker}...")
        stock = yf.Ticker(ticker)
        info = stock.info
        print(f"Success! Country: {info.get('country')}")
    except Exception as e:
        print(f"Error for {ticker}: {e}")
        import traceback
        traceback.print_exc()
