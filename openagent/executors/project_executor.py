import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Type

import aiohttp
from aiocache import Cache
from aiocache.decorators import cached
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from openagent.conf.env import settings

API_KEY = ""
HEADERS = {
    "apikey": settings.ROOTDATA_API_KEY,
    "language": "en",
    "Content-Type": "application/json",
}


class ARGS(BaseModel):
    keyword: str = Field(description="keyword")


def _fetch_project_sync(keyword: str) -> str:
    projects = asyncio.run(fetch_project(keyword))
    return json.dumps(projects)


class ProjectExecutor(BaseTool):
    name = "ProjectExecutor"

    description = "get the project information like investors, team members, social media, etc."
    args_schema: Type[ARGS] = ARGS

    def _run(
        self,
        keyword: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        if settings.ROOTDATA_API_KEY is None:
            return "Please set ROOTDATA_API_KEY in the environment"
        with ThreadPoolExecutor() as executor:
            future = executor.submit(_fetch_project_sync, keyword)
            return future.result()

    async def _arun(
        self,
        keyword: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        if settings.ROOTDATA_API_KEY is None:
            return "Please set ROOTDATA_API_KEY in the environment"
        projects = await fetch_project(keyword)
        return json.dumps(projects)


async def fetch_project_detail(session, project_id: int) -> dict:
    url = "https://api.rootdata.com/open/get_item"
    payload = json.dumps({"project_id": project_id, "include_team": True, "include_investors": True})

    async with session.post(url, headers=HEADERS, data=payload) as response:
        response_text = await response.text()
        return json.loads(response_text)["data"]


@cached(ttl=300, cache=Cache.MEMORY)
async def fetch_project(keyword: str) -> list:
    url = "https://api.rootdata.com/open/ser_inv"
    payload = json.dumps({"query": keyword, "variables": {}})

    async with aiohttp.ClientSession() as session, session.post(url, headers=HEADERS, data=payload) as response:
        response_text = await response.text()
        data = json.loads(response_text)["data"]
        project_ids = [item["id"] for item in data if item["type"] == 1][0:2]

        tasks = [fetch_project_detail(session, project_id) for project_id in project_ids]
        return list(await asyncio.gather(*tasks))


if __name__ == "__main__":
    print(asyncio.run(fetch_project("rss3")))
