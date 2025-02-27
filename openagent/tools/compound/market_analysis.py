import asyncio
from dataclasses import dataclass
from textwrap import dedent
from typing import Optional, List

from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from pydantic import BaseModel, Field
from openagent.agent.config import ModelConfig
from openagent.core.constants.chain_ids import CHAIN_ID_TO_NETWORK
from openagent.core.tool import Tool
from openagent.core.utils.fetch_json import fetch_json


@dataclass
class CompoundMarketData:
    address: str
    borrowAPR: float
    borrowAPRChange24h: float
    chain_id: int
    supplyAPR: float
    supplyAPRChange24h: float


class CompoundMarketConfig(BaseModel):
    model: Optional[ModelConfig] = Field(
        default=None,
        description="Model configuration for this tool. If not provided, will use agent's core model",
    )
    chain_ids: List[int] = Field(
        default_factory=[],
        description="List of chain IDs to fetch Compound market data from",
    )


class CompoundMarketTool(Tool[CompoundMarketConfig]):
    def __init__(self, core_model=None, chain_ids: List[int] = []):
        super().__init__()
        self.chain_ids = chain_ids
        self.core_model = core_model
        self.tool_model = None
        self.tool_prompt = None

    @property
    def name(self) -> str:
        return "compound_market_analysis"

    @property
    def description(self):
        return "You are a DeFi data analyst that analyze Compound markets' APR."

    async def setup(self, config: CompoundMarketConfig) -> None:
        model_config = config.model if config.model else self.core_model
        if not model_config:
            raise RuntimeError("No model configuration provided")

        self.tool_model = init_chat_model(
            model=model_config.name,
            model_provider=model_config.provider,
            temperature=model_config.temperature,
        )

        self.tool_prompt = PromptTemplate(
            template=dedent(
                f"""\
            {self.description}

            ### Data
            {{data}}

            ### Data Structure
            - Market object with:
              - `borrowAPR`: Current borrow APR
              - `supplyAPR`: Current supply APR
              - `borrowAPRChange24h`: 24h borrow APR change
              - `supplyAPRChange24h`: 24h supply APR change

            ### Task
            Analyze the market data and provide:
            - Must be concise with clear statements about APR changes
            - Include both supply and borrow APR changes
            - Include list of supported collateral assets
            - Do not provide personal opinions or financial advice\
            """
            ),
            input_variables=["data"],
        )

    async def __call__(self) -> str:
        logger.info(f"{self.name} tool is called.")

        if not self.tool_model:
            raise RuntimeError("Model not initialized")

        try:
            # Fetch Compound market data
            market_list = await self._fetch_compound_market_data(self.chain_ids)

            # Analyze market data
            chain = self.tool_prompt | self.tool_model | StrOutputParser()

            # Run analysis chain
            response = await chain.ainvoke(
                {
                    "data": market_list,
                }
            )

            logger.info(f"{self.name} tool response: {response.strip()}.")

            return response.strip()

        except Exception as e:
            logger.error(f"Error in {self.name} tool: {e}")
            return f"Error in {self.name} tool: {e}"

    @staticmethod
    async def _fetch_compound_market_data(
        chain_ids: List[int],
    ) -> list[CompoundMarketData]:
        results = await fetch_json(
            url="https://v3-api.compound.finance/market/all-networks/all-contracts/summary"
        )

        # Filter for chain_ids
        markets = [market for market in results if market["chain_id"] in chain_ids]

        if not markets:
            logger.warning("No markets found for the given chain_ids")
            return []

        async def fetch_historical_data(address: str, chain_id: int) -> dict:
            """Fetches historical data for a specific market market_address."""

            network = CHAIN_ID_TO_NETWORK.get(chain_id)
            network_path = f"{network}-" if network != "ethereum" else ""

            return await fetch_json(
                f"https://v3-api.compound.finance/market/{network_path}mainnet/{address}/historical/summary"
            )

        historical_data_list = await asyncio.gather(
            *[
                fetch_historical_data(market["comet"]["address"], market["chain_id"])
                for market in markets
            ]
        )

        market_data = []

        for market, historical_data in zip(markets, historical_data_list):
            market_address = market["comet"]["address"]

            if len(historical_data) < 2:
                logger.warning(f"Insufficient historical data for {market_address}")
                continue

            # Sort historical data by timestamp (descending)
            sorted_data = sorted(
                historical_data, key=lambda x: x["timestamp"], reverse=True
            )[:2]

            # Convert APR values from string to float
            # purposely not using get() so it throws an error if the key is missing
            # which indicates a data structure change with the API response
            current_borrow_apr = float(sorted_data[0]["borrow_apr"])
            current_supply_apr = float(sorted_data[0]["supply_apr"])
            yesterday_borrow_apr = float(sorted_data[1]["borrow_apr"])
            yesterday_supply_apr = float(sorted_data[1]["supply_apr"])

            # Calculate 24h APR changes
            borrow_apr_change_24h = current_borrow_apr - yesterday_borrow_apr
            supply_apr_change_24h = current_supply_apr - yesterday_supply_apr

            market_data.append(
                CompoundMarketData(
                    address=market_address,
                    borrowAPR=current_borrow_apr,
                    borrowAPRChange24h=borrow_apr_change_24h,
                    chain_id=market["chain_id"],
                    supplyAPR=current_supply_apr,
                    supplyAPRChange24h=supply_apr_change_24h,
                )
            )

        return market_data
