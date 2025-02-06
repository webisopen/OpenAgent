import asyncio

from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openai import OpenAIChat

load_dotenv()


async def main():
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="you are assistant!",
        tools=[
            YFinanceTools(
                stock_price=True, analyst_recommendations=True, company_info=True
            )
        ],
        add_history_to_messages=True,
        markdown=True,
        storage=SqliteAgentStorage(table_name="agent_sessions", db_file="tmp/data.db"),
    )
    session_id = ("test7",)
    agent.session_id = session_id
    agent.print_response("i am bob", show_reasoning=True, show_full_reasoning=True)
    agent.session_id = session_id

    agent.print_response("who  am i", show_reasoning=True, show_full_reasoning=True)


if __name__ == "__main__":
    asyncio.run(main())
