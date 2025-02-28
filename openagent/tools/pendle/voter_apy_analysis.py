import os
from datetime import datetime, UTC
from textwrap import dedent
from typing import Optional

import httpx
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from openagent.agent.config import ModelConfig
from openagent.core.database.engine import create_engine
from openagent.core.tool import Tool
from openagent.core.utils.fetch_json import fetch_json
from openagent.core.utils.json_equal import json_equal

Base = declarative_base()


class PendleVoterApy(Base):
    __tablename__ = "pendle_voter_apy"

    id = Column(Integer, primary_key=True)
    data = Column(String)  # json response
    created_at = Column(DateTime, default=datetime.now(UTC))


class PendleVoterApyConfig(BaseModel):
    """Configuration for data analysis tool"""

    model: Optional[ModelConfig] = Field(
        default=None,
        description="Model configuration for LLM. If not provided, will use agent's core model",
    )


class PendleVoterApyTool(Tool[PendleVoterApyConfig]):
    """Tool for analyzing data changes using a model"""

    def __init__(self, core_model=None):
        super().__init__()
        self.core_model = core_model
        self.tool_model = None
        self.tool_prompt = None
        db_path = 'sqlite:///' + os.path.join(os.getcwd(), "storage", f"{self.name}.db")
        self.engine = create_engine("sqlite", db_path)
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
        model_config = config.model if config.model else self.core_model
        if not model_config:
            raise RuntimeError("No model configuration provided")

        self.tool_model = init_chat_model(
            model=model_config.name,
            model_provider=model_config.provider,
            temperature=model_config.temperature,
        )

        # Create prompt template
        template = dedent(
            f"""\
        {self.description}

        Data: {{data}}

        ### Data Structure
        `top_apy_increases`, `top_apy_decreases` are top 3 increases and decreases in voter APY:
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
        # Get Pendle voter data from API
        result = await fetch_json(
            url="https://api-v2.pendle.finance/bff/v1/ve-pendle/pool-voter-apy"
        )

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
            """Extract relevant pool information and convert APY to percentage format"""
            voter_apy = item["voterApy"]
            last_epoch_change = item["lastEpochChange"]

            # Determine change direction based on lastEpochChange
            # If change is positive -> increased, negative -> decreased
            change_direction = (
                "increased"
                if last_epoch_change > 0
                else "decreased" if last_epoch_change < 0 else "unchanged"
            )

            # Convert to percentage strings, use absolute value for lastEpochChange
            voter_apy_pct = f"{voter_apy * 100:.2f}%"
            last_epoch_pct = f"{abs(last_epoch_change * 100):.2f}%"

            return {
                "voterApy": voter_apy_pct,
                "lastEpochChange": last_epoch_pct,
                "name": item["pool"]["name"],
                "protocol": item["pool"]["protocol"],
                "change_direction": change_direction,
            }

        sorted_results = sorted(
            apy_data["results"], key=lambda x: x.get("lastEpochChange", 0), reverse=True
        )

        return {
            "top_apy_increases": [
                extract_pool_info(item) for item in sorted_results[:3]
            ],
            "top_apy_decreases": (
                [extract_pool_info(item) for item in sorted_results[-3:][::-1]]
                if len(sorted_results) > 3
                else []
            ),
        }
