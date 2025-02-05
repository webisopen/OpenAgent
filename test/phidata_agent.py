import asyncio

from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openai import OpenAIChat


load_dotenv()


async def main():
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="You are an enthusiastic news reporter with a flair for storytelling!",
        tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
        markdown=True
    )
    agent.print_response("Apple stock price", show_reasoning=True, show_full_reasoning=True)


if __name__ == "__main__":
    asyncio.run(main())
