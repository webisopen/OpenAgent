import yfinance as yf


def get_current_stock_price(symbol: str) -> str:
    """Use this function to get the current stock price for a given symbol.

    Args:
        symbol (str): The stock symbol.

    Returns:
        str: The current stock price or error message.
    """
    try:
        print("Fetching current price for", symbol)
        stock = yf.Ticker(symbol)
        # Use "regularMarketPrice" for regular market hours, or "currentPrice" for pre/post market
        current_price = stock.info.get(
            "regularMarketPrice", stock.info.get("currentPrice")
        )
        return (
            f"{current_price:.4f}"
            if current_price
            else f"Could not fetch current price for {symbol}"
        )
    except Exception as e:
        return f"Error fetching current price for {symbol}: {e}"
