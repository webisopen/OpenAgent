from dataclasses import dataclass
from datetime import datetime, timedelta
from textwrap import dedent
from typing import List, Optional

from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from pydantic import BaseModel, Field
from openagent.core.constants.chain_ids import CHAIN_ID_TO_NETWORK
from openagent.agent.config import ModelConfig
from openagent.core.tool import Tool
from openagent.core.utils.fetch_json import fetch_json

from typing import Optional
import undetected_chromedriver as uc
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@dataclass
class AaveMarketData:
    address: str
    symbol: str
    borrow_apr: float
    supply_apr: float
    borrow_apr_change_24h: float
    supply_apr_change_24h: float


class AaveMarketConfig(BaseModel):
    chain_ids: List[int] = Field(
        default_factory=[],
        description="List of chain IDs to fetch Aave market data from",
    )
    model: Optional[ModelConfig] = Field(
        default=None,
        description="Model configuration for this tool. If not provided, will use agent's core model",
    )


class AaveMarketTool(Tool[AaveMarketConfig]):
    def __init__(self, core_model=None):
        super().__init__()
        self.chain_ids = None
        self.core_model = core_model
        self.tool_model = None
        self.tool_prompt = None

    @property
    def name(self) -> str:
        return "aave_market_analysis"

    @property
    def description(self):
        return "You are a DeFi data analyst that analyze Aave markets' APY."

    async def setup(self, config: AaveMarketConfig) -> None:
        model_config = config.model if config.model else self.core_model
        if not model_config:
            raise RuntimeError("No model configuration provided")

        self.tool_model = init_chat_model(
            model=model_config.name,
            model_provider=model_config.provider,
            temperature=model_config.temperature,
        )

        self.chain_ids = config.chain_ids

        self.tool_prompt = PromptTemplate(
            template=dedent(
                f"""\
            {self.description}

            ### Data
            {{data}}

            ### Data Structure
            - Market object with:
              - `symbol`: Token symbol
              - `borrow_apr`: Current borrow APR
              - `supply_apr`: Current supply APR
              - `borrow_apr_change_24h`: 24h borrow APR change
              - `supply_aprChange24h`: 24h supply APR change

            ### Task
            Analyze the market data and provide:
            - Must be concise with clear statements about APR changes
            - Include both supply and borrow APR changes
            - Include token symbols
            - Do not provide personal opinions or financial advice\
            """
            ),
            input_variables=["data"],
        )

    async def __call__(self, data: str) -> str:
        logger.info(f"{self.name} tool is called.")

        if not self.tool_model:
            raise RuntimeError("No model initialized")

        try:
            # Fetch market data for all configured chains
            market_list = []
            for chain_id in self.chain_ids:
                chain_markets = await self._fetch_aave_market_data(chain_id)
                market_list.extend(chain_markets)

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

    async def _fetch_aave_market_data(self, chain_id: int) -> list[AaveMarketData]:
        network = CHAIN_ID_TO_NETWORK.get(chain_id)
        if not network:
            logger.warning(f"Unsupported chain_id: {chain_id}")
            return []

        # Get the appropriate fetch method based on network
        fetch_method = getattr(self, f"_fetch_aave_{network}_market_data", None)

        if not fetch_method:
            logger.warning(f"No fetch method implemented for network: {network}")
            return []

        try:
            market_data = await fetch_method()

            # Sort market data by absolute supply APR change (descending)
            market_data.sort(key=lambda x: abs(x.supply_apr_change_24h), reverse=True)

            # Return top markets with largest changes
            return market_data[:3]
        except Exception as e:
            logger.error(f"Error fetching {network} market data: {e}")
            return []

    async def _fetch_aave_arbitrum_market_data(self) -> list[AaveMarketData]:
        # Initialize undetected-chromedriver with additional options
        driver = uc.Chrome(options=None, use_subprocess=False)

        try:
            driver.get(
                "https://api.de.fi/v1/opportunities?first=30&sortDirection=DESC&sortField=apr&platformIds[]=3&chains[]=5"
            )

            body = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            content = body.text

            results = json.loads(content)

            if not results.get("items"):
                raise Exception("Invalid data structure: 'items' not found")
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return []

        market_data = []

        for item in results["items"]:
            if (
                    item.get("tokens", {}).get("borrows")
                    and len(item["tokens"]["borrows"]) > 0
            ):
                borrow_address = item["tokens"]["borrows"][0].get("address")
                if borrow_address:
                    market_data.append(
                        AaveMarketData(
                            address=borrow_address,
                            symbol=item["tokens"]["borrows"][0].get("symbol"),
                            borrow_apr=0,
                            supply_apr=0,
                            borrow_apr_change_24h=0,
                            supply_apr_change_24h=0,
                        )
                    )

        timestamp = int((datetime.now() - timedelta(days=2)).timestamp())

        for i in range(len(market_data)):
            try:
                rates_history = await fetch_json(
                    f"https://aave-api-v2.aave.com/data/rates-history?reserveId={market_data[i].address}0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb42161&from={timestamp}&resolutionInHours=24"
                )

                def get_date(rate):
                    return datetime(
                        rate["x"]["year"], rate["x"]["month"] + 1, rate["x"]["date"]
                    ).date()

                today_data = next(
                    (
                        rate
                        for rate in rates_history
                        if get_date(rate) == datetime.now().date()
                    ),
                    None,
                )
                yesterday_data = next(
                    (
                        rate
                        for rate in rates_history
                        if get_date(rate) == datetime.now().date() - timedelta(days=1)
                    ),
                    None,
                )

                if not today_data or not yesterday_data:
                    logger.warning(f"Missing data for {market_data[i].address}")
                    continue

                # Update the existing market_data entry instead of appending
                market_data[i].borrow_apr = today_data["variableBorrowRate_avg"]
                market_data[i].supply_apr = today_data["liquidityRate_avg"]
                market_data[i].borrow_apr_change_24h = (
                        today_data["variableBorrowRate_avg"]
                        - yesterday_data["variableBorrowRate_avg"]
                )
                market_data[i].supply_apr_change_24h = (
                        today_data["liquidityRate_avg"]
                        - yesterday_data["liquidityRate_avg"]
                )
            except Exception as e:
                logger.warning(
                    f"Failed to fetch data for {market_data[i].address}: {e}"
                )
                continue

        return market_data
