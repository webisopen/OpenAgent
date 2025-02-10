from typing import Optional, Dict, List

import aiohttp
from aiocache import Cache
from aiocache.decorators import cached
from loguru import logger


def chain_name_to_id(chain_name: str) -> str:
    """
    Convert chain name to chain ID.

    Args:
        chain_name (str): The name of the blockchain network.

    Returns:
        str: The corresponding chain ID.
    """
    chain_map = {
        "ETH": "1",
        "OPTIMISM": "10",
        "BSC": "56",
        "BASE": "8453",
        "ARBITRUM": "42161",
    }
    return chain_map.get(chain_name, "1")


async def select_best_token(keyword: str, chain_id: str) -> Optional[Dict]:
    """
    Select the best token based on the keyword and chain ID.

    Args:
        keyword (str): The keyword to search for.
        chain_id (str): The chain ID to filter tokens.

    Returns:
        Optional[Dict]: The best matching token, or None if no match is found.
    """
    keyword = keyword.lower()

    # special case for eth on non-ethereum chains
    if keyword == "eth" and chain_id != "1":
        keyword = "weth"

    # special case for btc
    if keyword == "btc":
        keyword = "wbtc"

    tokens = await fetch_tokens()
    tokens_on_chain = tokens.get(chain_id, [])

    # Filter based on symbol and name
    results = [
        token
        for token in tokens_on_chain
        if token["symbol"].lower() == keyword or token["name"].lower() == keyword
    ]

    if results:
        if len(results) == 1:
            return results[0]

        # Sort based on priority
        results.sort(
            key=lambda x: (
                "logoURI" in x,
                x["symbol"].lower() == keyword,
                x.get("coinKey", "").lower() == keyword,
                x.get("priceUSD") is not None,
                x["name"].lower() == keyword,
            ),
            reverse=True,
        )
        return results[0]

    return None


@cached(ttl=300, cache=Cache.MEMORY)
async def fetch_tokens() -> Dict[str, List[Dict]]:
    """
    Fetch the token list from the API and cache it for 60 seconds.

    Returns:
        Dict[str, List[Dict]]: The token list grouped by chain ID.
    """
    url = "https://li.quest/v1/tokens"
    headers = {"Accept": "application/json"}
    logger.info(f"Fetching new data from {url}")

    async with aiohttp.ClientSession() as session:  # noqa
        async with session.get(url, headers=headers) as response:
            token_list = await response.json()
            return token_list["tokens"]


def get_token_data_by_key(token: Dict, key: str) -> str:
    """
    Retrieve data from the token dictionary by key.

    Args:
        token (Dict): The token dictionary.
        key (str): The key to retrieve the data.

    Returns:
        str: The value associated with the key, or an empty string if the key does not exist.
    """
    return str(token[key]) if token and key in token else ""
