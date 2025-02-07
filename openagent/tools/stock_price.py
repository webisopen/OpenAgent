import yfinance as yf
from pydantic import BaseModel

from openagent.core.interfaces.tool import Tool


class StockPriceConfig(BaseModel):
    """Configuration for the stock price function"""

    use_regular_market: bool = (
        True  # If True, use regularMarketPrice, else use currentPrice
    )


class GetCurrentStockPrice(Tool):
    """Function to get current stock price"""

    @property
    def name(self) -> str:
        return "get_current_stock_price"

    @property
    def description(self) -> str:
        return "Get the current stock price for a given symbol"

    def __init__(self):
        super().__init__()
        self.config: StockPriceConfig | None = None

    async def setup(self, config: StockPriceConfig) -> None:
        """Setup the function with configuration"""
        self.config = config

    def __call__(self, symbol: str) -> str:
        """Get the current stock price for a given symbol.

        Args:
            symbol (str): The stock symbol.

        Returns:
            str: The current stock price or error message.
        """
        try:
            print("Fetching current price for", symbol)
            stock = yf.Ticker(symbol)

            # Use configured price type
            if self.config and self.config.use_regular_market:
                current_price = stock.info.get("regularMarketPrice")
            else:
                current_price = stock.info.get("currentPrice")

            if not current_price:
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


if __name__ == "__main__":
    print(GetCurrentStockPrice().to_function())
