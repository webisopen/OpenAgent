from phi.agent import Agent
from phi.tools.yfinance import YFinanceTools

finance_agent = Agent(
    name="Finance Agent",
    tools=[YFinanceTools(stock_price=True)],
)
