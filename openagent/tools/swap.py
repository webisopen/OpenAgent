import asyncio
from typing import Literal
from openagent.tools.token_utils import (
    chain_name_to_id,
    select_best_token,
    get_token_data_by_key,
)
from pydantic import BaseModel

ChainLiteral = Literal["ETH", "BSC", "ARBITRUM", "OPTIMISM", "BASE"]


class Swap(BaseModel):
    from_token: str
    from_token_address: str
    to_token: str
    to_token_address: str
    amount: str
    type: str = "swap"
    from_chain_name: str
    to_chain_name: str


async def fetch_swap(
    from_token: str,
    to_token: str,
    from_chain: ChainLiteral,
    to_chain: ChainLiteral,
    amount: str,
):
    """
    Fetch the swap details for the given parameters.

    Args:
        from_token (str): The symbol of the from-side token.
        to_token (str): The symbol of the to-side token.
        from_chain (ChainLiteral): The from-side blockchain network.
        to_chain (ChainLiteral): The to-side blockchain network.
        amount (str): The amount of tokens to swap.

    Returns:
        str: The swap details in JSON format.
    """
    from_chain_id = chain_name_to_id(from_chain)
    to_chain_id = chain_name_to_id(to_chain)

    # Fetch token data concurrently
    from_token_data, to_token_data = await asyncio.gather(
        select_best_token(from_token, from_chain_id),
        select_best_token(to_token, to_chain_id),
    )

    swap = Swap(
        from_token=get_token_data_by_key(from_token_data, "symbol"),
        from_token_address=get_token_data_by_key(from_token_data, "address"),
        to_token=get_token_data_by_key(to_token_data, "symbol"),
        to_token_address=get_token_data_by_key(to_token_data, "address"),
        from_chain_name=from_chain,
        to_chain_name=to_chain,
        amount=amount,
    )
    return swap.model_dump_json()
