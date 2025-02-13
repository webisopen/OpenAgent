import json
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from typing import List
import aiohttp
from pydantic import BaseModel, Field
from textwrap import dedent
from loguru import logger

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model
from openagent.agent.config import ModelConfig
from openagent.core.tool import Tool

Base = declarative_base()

PENDLE_MARKET_CONFIG = {
    "url": "https://api-v2.pendle.finance/bff/v3/markets/all?isActive=true",
    "description": """
    This data contains Pendle Market information with the following key metrics:
    
    For each yield pool:
    - Symbol: The pool identifier
    - New pool status: Whether it's a newly added pool
    - 24h liquidity change: Liquidity change in the last 24 hours
    - 24h implied APY change: APY change in the last 24 hours
    
    The data also includes rankings for:
    - Top 3 pools by 24h liquidity change
    - Top 3 new pools by 24h liquidity change
    - Top 3 pools by APY change
    - Top 3 new pools by APY change
    """
}

@dataclass
class PendleYieldData:
    symbol: str
    isNew: bool
    liquidityChange24h: float
    impliedApyChange24h: float

    
@dataclass
class PendleMarketSnapshot:
    yieldList: List[PendleYieldData]
    liquidityChangeTopList: List[str]
    newLiquidityChangeTopList: List[str]
    apyChangeTopList: List[str]
    newApyChangeTopList: List[str]
    
class PendleMarket(Base):
    __tablename__ = "pendle_market"

    id = Column(Integer, primary_key=True)
    data = Column(String)  # json response
    created_at = Column(DateTime, default=datetime.now(UTC))

class PendleMarketConfig(BaseModel):
    """Configuration for data analysis tool"""

    model: ModelConfig = Field(description="Model configuration for LLM")

class PendleMarketTool(Tool[PendleMarketConfig]):
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
        return "pendle_market_analysis"

    @property
    def description(self) -> str:
        return "You are a DeFi data analysis expert focusing on positive market movements"

    async def setup(self, config: PendleMarketConfig) -> None:
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
        
        Please analyze the Pendle Market data with the following structure:

        1. Top Performers Analysis:
           - Analyze the top 3 pools by liquidity change (liquidity_change_top_list)
           - Analyze the top 3 new pools by liquidity change (new_liquidity_change_top_list)
           - Analyze the top 3 pools by APY change (apy_change_top_list)
           - Analyze the top 3 new pools by APY change (new_apy_change_top_list)

        For each pool in these rankings:
        - Find its detailed data in yieldList
        - Highlight positive metrics (liquidity increases, APY improvements)
        - Identify emerging trends and new opportunities
        - Track successful new pool launches, for new pools: Clearly mark as "NEW" and highlight their initial performance

        Rules:
        - Keep each pool analysis to 1-2 concise sentences
        - Only mention positive percentage changes
        - Skip any negative growth metrics
        - Do not provide any personal opinions or financial advice
        - Clearly distinguish between new pools and established pools
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
            # Fetch the latest data from Pendle API
            latest_data = await self._fetch_pendle_market_data()

            # Save new data to database
            self.session.add(latest_data)
            self.session.commit()

            chain = self.tool_prompt | self.tool_model | StrOutputParser()

            # Run analysis chain
            response = await chain.ainvoke(
                {
                    "description": dedent(PENDLE_MARKET_CONFIG["description"]),
                    "data": latest_data.data,
                }
            )

            return response.strip()

        except Exception as e:
            error_msg = f"Error analyzing data: {e}"
            logger.error(error_msg)
            return error_msg

    async def _fetch_pendle_market_data(self) -> PendleMarket:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method="GET", url=PENDLE_MARKET_CONFIG["url"]
            ) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")

                # Get response data
                results = json.loads(await response.text())

                # Process the data
                snapshot = self._process_market_data(results)
                              
                return PendleMarket(
                    data=json.dumps(asdict(snapshot)),
                    created_at=datetime.now(UTC),
                )
                
    def _process_market_data(self, results: dict) -> PendleMarketSnapshot:
            """Process raw market data into a structured snapshot"""
            
            # Create yield data list
            yield_data_list = []
            for i in range(len(results['symbolList'])):
                yield_info = PendleYieldData(
                    symbol=results['symbolList'][i],
                    isNew=results['isNewList'][i],
                    liquidityChange24h=results['liquidityChange24hList'][i],
                    impliedApyChange24h=results['impliedApyChange24hList'][i],
                )
                yield_data_list.append(yield_info)

            # Top 3 by 24h liquidity change
            liquidity_change_top = sorted(yield_data_list, key=lambda x: x.liquidityChange24h, reverse=True)[:3]
            liquidity_change_top_symbols = [market.symbol for market in liquidity_change_top]
                
            # Top 3 new pools by 24h liquidity change
            new_pools = [market for market in yield_data_list if market.isNew]
            new_liquidity_change_top = sorted(new_pools, key=lambda x: x.liquidityChange24h, reverse=True)[:3]
            new_liquidity_change_top_symbols = [market.symbol for market in new_liquidity_change_top]

            # Top 3 by APY change
            apy_change_top = sorted(yield_data_list, key=lambda x: x.impliedApyChange24h, reverse=True)[:3]
            apy_change_top_symbols = [market.symbol for market in apy_change_top]

            # Top 3 new pools by APY change
            new_apy_change_top = sorted(new_pools, key=lambda x: x.impliedApyChange24h, reverse=True)[:3]
            new_apy_change_top_symbols = [market.symbol for market in new_apy_change_top]
            
            # Filter yield data to only include ranked pools
            relevant_symbols = set(liquidity_change_top_symbols + 
                                new_liquidity_change_top_symbols + 
                                apy_change_top_symbols + 
                                new_apy_change_top_symbols)
            
            filtered_yield_data = [data for data in yield_data_list 
                                if data.symbol in relevant_symbols]

            return PendleMarketSnapshot(
                yieldList=filtered_yield_data,
                liquidityChangeTopList=liquidity_change_top_symbols,
                newLiquidityChangeTopList=new_liquidity_change_top_symbols,
                apyChangeTopList=apy_change_top_symbols,
                newApyChangeTopList=new_apy_change_top_symbols
            )