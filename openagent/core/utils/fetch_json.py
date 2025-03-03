from typing import Dict, Optional, Any

import httpx
from loguru import logger


async def fetch_json(
    url: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    **kwargs,
) -> Dict:
    """
    Fetches JSON data from a given URL using an HTTP request.

    :param url: The API endpoint.
    :param method: HTTP method ('GET', 'POST', etc.), defaults to 'GET'.
    :param params: Optional query parameters.
    :param headers: Optional request headers.
    :param timeout: Request timeout in seconds (default 30.0).
    :param kwargs: Additional arguments for request customization.
    :return: JSON response as a dictionary.
    :raises httpx.HTTPStatusError: If the response contains an error status.
    :raises httpx.RequestError: If a network error occurs.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(
                method=method, url=url, params=params, headers=headers, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} for URL {url}: {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for URL {url}: {e}")
            raise
