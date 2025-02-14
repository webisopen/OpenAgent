import json
from datetime import datetime, UTC
from textwrap import dedent

import aiohttp
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from openagent.agent.config import ModelConfig
from openagent.core.tool import Tool
from openagent.core.utils.json_equal import json_equal

Base = declarative_base()

POOL_VOTER_APY_CONFIG = {
    "url": "https://api-v2.pendle.finance/bff/v1/ve-pendle/pool-voter-apy",
    "description": """\
        Voter APY data for Pendle pools.
        Data Structure:
            `top_apy_increases`, `top_apy_decreases` are top 5 increases and decreases in voter APY:
                - name:              Pool name
                - protocol:          Protocol name
                - voterApy:          Current APY
                - lastEpochChange:   Voter APY change\
        """,
}


class PendleVoterApy(Base):
    __tablename__ = "pendle_voter_apy"

    id = Column(Integer, primary_key=True)
    uri = Column(String)  # api endpoint
    data = Column(String)  # json response
    created_at = Column(DateTime, default=datetime.now(UTC))


class PendleVoterApyConfig(BaseModel):
    """Configuration for data analysis tool"""

    model: ModelConfig = Field(description="Model configuration for LLM")


class PendleVoterApyTool(Tool[PendleVoterApyConfig]):
    """Tool for analyzing data changes using LLM"""

    def __init__(self):
        super().__init__()
        self.tool_model = None
        self.tool_prompt = None
        self.engine = create_engine("sqlite:///storage/pendle_data_analysis.db")
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    @property
    def name(self) -> str:
        return "pendle_voter_apy_analysis"

    @property
    def description(self) -> str:
        return """You are a DeFi data analysis expert.
        You analyze the latest Pendle Voter APY changes to provide a structured report.
        """

    async def setup(self, config: PendleVoterApyConfig) -> None:
        """Setup the analysis tool with LLM chain"""

        # Initialize LLM
        self.tool_model = init_chat_model(
            model=config.model.name,
            model_provider=config.model.provider,
            temperature=config.model.temperature,
        )

        # Create prompt template
        template = """
        {description}

        Data: {data}

        You must use the following fields in your analysis:
        - name
        - protocol
        - voterApy
        - lastEpochChange

        For each pool in data, give 1-2 concise sentences about the pool's APY change.
        Do not provide any personal opinions or financial advices.
        """

        self.tool_prompt = PromptTemplate(
            template=template, input_variables=["description", "data"]
        )

    async def __call__(self) -> str:
        """
        Analyze data using LLM

        Returns:
            str: Analysis results from the LLM
        """
        if not self.tool_model:
            raise RuntimeError("Tool not properly initialized. Call setup() first.")

        try:
            # Query existing data from database
            existing_data = (
                self.session.query(PendleVoterApy)
                .order_by(PendleVoterApy.created_at.desc())
                .first()
            )

            # Fetch the latest data from Pendel API
            latest_data = await self._fetch_pendle_voter_apy()

            # Compare both datasets
            if existing_data:
                if json_equal(existing_data.data, latest_data.data):
                    return "APY data has no change."

            # Save new data to database
            self.session.add(latest_data)
            self.session.commit()

            chain = self.tool_prompt | self.tool_model | StrOutputParser()
            # Run analysis chain
            response = await chain.ainvoke(
                {
                    "description": dedent(POOL_VOTER_APY_CONFIG["description"]),
                    "data": latest_data.data,
                }
            )

            return response.strip()

        except Exception as e:
            error_msg = f"Error analyzing data: {e}"
            logger.error(error_msg)
            return error_msg

    async def _fetch_pendle_voter_apy(self) -> PendleVoterApy:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method="GET", url=POOL_VOTER_APY_CONFIG["url"]
            ) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")

                # Get response data
                result = json.loads(await response.text())

                if not result["results"]:
                    raise Exception("API response is empty")

                data = self._filter_pendle_voter_apy(result)

                # Create new snapshot
                snapshot = PendleVoterApy(
                    uri=POOL_VOTER_APY_CONFIG["url"],
                    data=str(data),
                    created_at=datetime.now(UTC),
                )

                return snapshot

    @staticmethod
    def _filter_pendle_voter_apy(apy_data: dict) -> dict:
        """Filter pool voter apy data"""

        def extract_pool_info(item: dict) -> dict:
            """Extract relevant pool information"""
            root_fields = ("voterApy", "lastEpochChange")
            pool_fields = ("name", "protocol")

            return {
                **{k: item[k] for k in root_fields},
                **{k: item["pool"][k] for k in pool_fields},
            }

        sorted_results = sorted(
            apy_data["results"], key=lambda x: x.get("lastEpochChange", 0), reverse=True
        )

        return {
            "top_apy_increases": [
                extract_pool_info(item) for item in sorted_results[:5]
            ],
            "top_apy_decreases": (
                [extract_pool_info(item) for item in sorted_results[-5:][::-1]]
                if len(sorted_results) > 5
                else []
            ),
        }
