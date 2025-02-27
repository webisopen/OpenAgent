from dataclasses import dataclass
from textwrap import dedent
from typing import Optional

import httpx
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from pydantic import BaseModel, Field
from openagent.agent.config import ModelConfig
from openagent.core.tool import Tool
from openagent.core.utils.fetch_json import fetch_json


@dataclass
class CompoundMarketData:
    address: str
    collateralAssets: list[str]
    borrowAPR: float
    supplyAPR: float
    borrowAPRChange24h: float
    supplyAPRChange24h: float


class CompoundMarketConfig(BaseModel):
    model: Optional[ModelConfig] = Field(
        default=None,
        description="Model configuration for this tool. If not provided, will use agent's core model",
    )


class ArbitrumCompoundMarketTool(Tool[CompoundMarketConfig]):
    def __init__(self, core_model=None):
        super().__init__()
        self.core_model = core_model
        self.tool_model = None
        self.tool_prompt = None

    @property
    def name(self) -> str:
        return "arbitrum_compound_market_analysis"

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
              - `collateralAssets`: List of supported collateral assets
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
            # Fetch Compound arbitrum-network market data
            arbitrum_market_list = await self._fetch_compound_arbitrum_market_data()

            # Analyze market data
            chain = self.tool_prompt | self.tool_model | StrOutputParser()

            # Run analysis chain
            response = await chain.ainvoke(
                {
                    "data": arbitrum_market_list,
                }
            )

            logger.info(f"{self.name} tool response: {response.strip()}.")

            return response.strip()

        except Exception as e:
            logger.error(f"Error in {self.name} tool: {e}")
            return f"Error in {self.name} tool: {e}"

    @staticmethod
    async def _fetch_compound_arbitrum_market_data() -> list[CompoundMarketData]:
        results = await fetch_json(
            url="https://v3-api.compound.finance/market/all-networks/all-contracts/summary"
        )

        # Filter for Arbitrum markets (chain_id 42161)
        arbitrum_markets = [market for market in results if market["chain_id"] == 42161]

        market_data = []

        for market in arbitrum_markets:
            # Fetch historical data for each address
            historical_data = await fetch_json(
                f"https://v3-api.compound.finance/market/arbitrum-mainnet/{market['comet']['address']}/historical/summary"
            )

            # Sort historical data by timestamp in descending order (newest first)
            sorted_data = sorted(
                historical_data, key=lambda x: x["timestamp"], reverse=True
            )

            if len(sorted_data) < 2:
                logger.warning(
                    f"Insufficient historical data for {market['comet']['address']}"
                )
                continue

            # Convert string APRs to float
            current_borrow_apr = float(sorted_data[0]["borrow_apr"])
            current_supply_apr = float(sorted_data[0]["supply_apr"])
            yesterday_borrow_apr = float(sorted_data[1]["borrow_apr"])
            yesterday_supply_apr = float(sorted_data[1]["supply_apr"])

            # Calculate 24h changes
            borrow_apr_change_24h = current_borrow_apr - yesterday_borrow_apr
            supply_apr_change_24h = current_supply_apr - yesterday_supply_apr

            market_data.append(
                CompoundMarketData(
                    address=market["comet"]["address"],
                    collateralAssets=market["collateral_asset_symbols"],
                    borrowAPR=current_borrow_apr,
                    supplyAPR=current_supply_apr,
                    borrowAPRChange24h=borrow_apr_change_24h,
                    supplyAPRChange24h=supply_apr_change_24h,
                )
            )

        return market_data
