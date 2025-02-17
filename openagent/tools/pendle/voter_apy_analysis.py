import os
from datetime import datetime, UTC
from textwrap import dedent

import aiohttp
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from openagent.agent.config import ModelConfig
from openagent.core.database import sqlite
from openagent.core.tool import Tool
from openagent.core.utils.json_equal import json_equal

Base = declarative_base()


class PendleVoterApy(Base):
    __tablename__ = "pendle_voter_apy"

    id = Column(Integer, primary_key=True)
    data = Column(String)  # json response
    created_at = Column(DateTime, default=datetime.now(UTC))


class PendleVoterApyConfig(BaseModel):
    """Configuration for data analysis tool"""

    model: ModelConfig = Field(description="Model configuration")


class PendleVoterApyTool(Tool[PendleVoterApyConfig]):
    """Tool for analyzing data changes using a model"""

    def __init__(self):
        super().__init__()
        self.tool_model = None
        self.tool_prompt = None
        db_path = os.path.join(os.getcwd(), "storage", f"{self.name}.db")
        self.engine = sqlite.create_engine(db_path)
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    @property
    def name(self) -> str:
        return "pendle_voter_apy_analysis"

    @property
    def description(self) -> str:
        return """
        You are a data analyst that analyze Pendle voter APY.
        """

    async def setup(self, config: PendleVoterApyConfig) -> None:
        """Setup the analysis tool with model and prompt"""

        # Initialize LLM
        self.tool_model = init_chat_model(
            model=config.model.name,
            model_provider=config.model.provider,
            temperature=config.model.temperature,
        )

        # Create prompt template
        template = dedent(
            f"""\
        {self.description}

        Data: {{data}}

        ### Data Structure
        `top_apy_increases`, `top_apy_decreases` are top 5 increases and decreases in voter APY:
            - name:              Pool name
            - protocol:          Protocol that issued the pool on Pendle
            - voterApy:          Current APY (not finalized for this epoch)
            - lastEpochChange:   Voter APY change in the last epoch, each epoch is 1 week

        ### Task
        Provide an analysis of the data:
        - Must include `name`, `protocol`, `voterApy`, `lastEpochChange`
        - Must be concise with 1 sentence per pool
        - Do not provide personal opinions or financial advice
        - Example: `name` (`protocol`) current voter APY `voterApy`, increased/decreased from last epoch `lastEpochChange`.\
        """
        )

        self.tool_prompt = PromptTemplate(template=template, input_variables=["data"])

    async def __call__(self) -> str:
        """
        Analyze data using the model

        Returns:
            str: Analysis results from the model
        """
        logger.info(f"{self.name} tool is called.")
        if not self.tool_model:
            raise RuntimeError("Tool not properly initialized. Call setup() first.")

        try:
            # Query existing data from database
            existing_data = (
                self.session.query(PendleVoterApy)
                .order_by(PendleVoterApy.created_at.desc())
                .first()
            )

            # Fetch the latest data from Pendle API
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
                    "data": latest_data.data,
                }
            )

            logger.info(f"{self.name} tool response: {response.strip()}.")
            return response.strip()

        except Exception as e:
            error_msg = f"Error analyzing data: {e}"
            logger.error(error_msg)
            return error_msg

    async def _fetch_pendle_voter_apy(self) -> PendleVoterApy:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method="GET",
                url="https://api-v2.pendle.finance/bff/v1/ve-pendle/pool-voter-apy",
            ) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")

                # Get response data
                result = await response.json()

                if not result["results"]:
                    raise Exception("API response is empty")

                data = self._filter_pendle_voter_apy(result)

                # Create new snapshot
                snapshot = PendleVoterApy(
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
