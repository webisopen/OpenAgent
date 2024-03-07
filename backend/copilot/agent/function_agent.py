from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, ChatMessageHistory
from langchain.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from toolz import memoize

from copilot.agent.cache import init_cache
from copilot.agent.postgres_history import PostgresChatMessageHistory
from copilot.agent.system_prompt import SYSTEM_PROMPT
from copilot.tool.feed_tool import FeedTool
from copilot.tool.google_tool import GoogleTool
from copilot.tool.network_tool import NetworkTool
from copilot.tool.collection_tool import CollectionTool
from copilot.tool.token_tool import TokenTool
from copilot.tool.dapp_tool import DappTool
from copilot.tool.account_tool import AccountTool
from copilot.tool.swap_tool import SwapTool
from copilot.tool.transfer_tool import TransferTool
from copilot.tool.wallet_tool import WalletTool
from copilot.conf.env import settings

init_cache()


@memoize
def get_agent(session_id: str) -> AgentExecutor:
    message_history = (
        get_msg_history(session_id) if session_id else ChatMessageHistory()
    )
    agent_kwargs = {
        "system_message": SystemMessage(content=SYSTEM_PROMPT),
        "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
    }
    memory = ConversationBufferMemory(
        memory_key="memory", return_messages=True, chat_memory=message_history
    )
    llm = ChatOpenAI(
        openai_api_base=settings.API_BASE,
        temperature=0.3,
        model="gpt-3.5-turbo-1106",
        streaming=True,
    )
    tools = [
        GoogleTool(),
        NetworkTool(),
        FeedTool(),
        CollectionTool(),
        TokenTool(),
        DappTool(),
        AccountTool(),
        SwapTool(),
        TransferTool(),
        WalletTool(),
    ]
    return initialize_agent(
        tools,
        llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        agent_kwargs=agent_kwargs,
        memory=memory,
        handle_parsing_errors=True,
    )


def get_msg_history(session_id):
    return PostgresChatMessageHistory(
        session_id=session_id,
    )