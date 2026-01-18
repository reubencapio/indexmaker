import yfinance as yf


def test_yfinance_features():
    print("Testing yfinance...")
    ticker = yf.Ticker("AAPL")

    # Test 1: ESG (Sustainability)
    print("\n--- Testing ESG (AAPL) ---")
    try:
        esg = ticker.sustainability
        if esg is not None and not esg.empty:
            print("ESG Data found:")
            print(esg.loc["totalEsg"])
        else:
            print("No ESG data found.")
    except Exception as e:
        print(f"ESG Error: {e}")

    # Test 2: Dividend Yield
    print("\n--- Testing Dividends/Yield (AAPL) ---")
    try:
        info = ticker.info
        div_yield = info.get("dividendYield")
        print(f"Dividend Yield: {div_yield}")

        dividends = ticker.dividends
        print(f"Dividend History (last 5): \n{dividends.tail(5)}")
    except Exception as e:
        print(f"Dividend Error: {e}")


if __name__ == "__main__":
    test_yfinance_features()
