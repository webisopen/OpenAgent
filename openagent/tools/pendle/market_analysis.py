import json
import os
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from heapq import nlargest
from typing import Optional, Literal

import httpx
from pydantic import BaseModel, Field
from textwrap import dedent
from loguru import logger

from sqlalchemy import Column, Integer, String, DateTime, create_engine as sa_create_engine, text as sa_text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model
from openagent.agent.config import ModelConfig
from openagent.core.database import sqlite
from openagent.core.tool import Tool

Base = declarative_base()


@dataclass
class PendleMarketData:
    """Data of a Pendle market, required for analysis"""

    symbol: str
    protocol: str
    isNewPool: bool
    liquidityChange24h: float
    impliedApyChange24h: float


@dataclass
class PendleMarketSnapshot:
    markets: list[PendleMarketData]
    liquidityIncreaseList: list[str]
    newMarketLiquidityIncreaseList: list[str]
    apyIncreaseList: list[str]
    newMarketApyIncreaseList: list[str]


class PendleMarket(Base):
    __tablename__ = "pendle_market"

    id = Column(Integer, primary_key=True)
    data = Column(String)  # json response
    created_at = Column(DateTime, default=datetime.now(UTC))


class DatabaseConfig(BaseModel):
    """Database configuration for the tool"""
    type: Literal["sqlite", "postgres"] = Field(
        default="sqlite",
        description="Type of database to use"
    )
    url: Optional[str] = Field(
        default=None,
        description="Database URL. For postgres: postgresql://user:password@host:port/database, for sqlite: sqlite:///path/to/file.db"
    )


class PendleMarketConfig(BaseModel):
    """Configuration for data analysis tool"""

    model: Optional[ModelConfig] = Field(
        default=None,
        description="Model configuration for LLM. If not provided, will use agent's core model",
    )
    database: Optional[DatabaseConfig] = Field(
        default=None,
        description="Database configuration. If not provided, will use SQLite with default path",
    )


class PendleMarketTool(Tool[PendleMarketConfig]):
    """Tool for analyzing data changes using a model"""

    def __init__(self, core_model=None):
        super().__init__()
        self.core_model = core_model
        self.tool_model = None
        self.tool_prompt = None
        self.engine = None
        self.session = None

    def _init_database(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize database connection based on configuration"""
        if not config:
            # Default to SQLite with default path
            db_path = os.path.join(os.getcwd(), "storage", f"{self.name}.db")
            if not os.path.exists(os.path.dirname(db_path)):
                os.makedirs(os.path.dirname(db_path))
            self.engine = sqlite.create_engine(db_path)
        else:
            if config.type == "sqlite":
                if config.url:
                    self.engine = sa_create_engine(config.url)
                else:
                    db_path = os.path.join(os.getcwd(), "storage", f"{self.name}.db")
                    if not os.path.exists(os.path.dirname(db_path)):
                        os.makedirs(os.path.dirname(db_path))
                    self.engine = sqlite.create_engine(db_path)
            else:  # postgres
                if not config.url:
                    raise ValueError("Database URL is required for PostgreSQL configuration")
                
                # Parse the database URL to get the database name and connection info
                from urllib.parse import urlparse
                url = urlparse(config.url)
                db_name = url.path[1:]  # Remove leading '/'
                base_url = f"{url.scheme}://{url.netloc}"

                # Create a connection to the default postgres database
                default_engine = sa_create_engine(f"{base_url}/postgres")
                default_conn = default_engine.connect()
                default_conn.execute(sa_text("commit"))  # Close any open transactions

                try:
                    # Check if database exists
                    result = default_conn.execute(sa_text(f"SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_name})
                    if not result.scalar():
                        # Create database if it doesn't exist
                        default_conn.execute(sa_text("commit"))
                        default_conn.execute(sa_text(f'CREATE DATABASE "{db_name}"'))
                        logger.info(f"Created database {db_name}")
                except Exception as e:
                    logger.error(f"Error creating database: {e}")
                finally:
                    default_conn.close()
                    default_engine.dispose()

                # Connect to the target database
                self.engine = sa_create_engine(config.url)

        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    @property
    def name(self) -> str:
        return "pendle_market_analysis"

    @property
    def description(self) -> str:
        return "You are a DeFi data analyst that analyze Pendle markets' APY and liquidity."

    async def setup(self, config: PendleMarketConfig) -> None:
        """Setup the analysis tool with model and prompt"""

        # Initialize database
        self._init_database(config.database)

        # Initialize the model
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
            - Markets: List of market objects with:
              - `symbol`: Name
              - `protocol`: Issuing protocol
              - `isNewPool`: Boolean (new market)
              - `liquidityChange24h`: 24h liquidity change
              - `impliedApyChange24h`: 24h APY change

            - Rankings
              - `liquidityIncreaseList`: Top 3 by liquidity change
              - `newMarketLiquidityIncreaseList`: Top 3 new markets by liquidity change
              - `apyIncreaseList`: Top 3 by APY increase
              - `newMarketApyIncreaseList`: Top 3 new markets by APY increase

            ### Task
            For each market in the rankings, provide an analysis:
            - Must be concise with 1 sentence per market, must include `symbol`, `protocol`, `liquidityChange24h`, `impliedApyChange24h`
            - For new markets: add "New Pool"
            - Do not provide personal opinions or financial advice\
            """
            ),
            input_variables=["data"],
        )

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
            # Fetch the latest data from Pendle API
            latest_data = await self._fetch_pendle_market_data()

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

    async def _fetch_pendle_market_data(self) -> PendleMarket:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api-v2.pendle.finance/bff/v3/markets/all?isActive=true"
            )
            if response.status_code != 200:
                raise Exception(
                    f"API request failed with status {response.status_code}"
                )

            # Get Pendle market data from API
            results = response.json()

            # Process the data
            snapshot = self._process_market_data(results)

            return PendleMarket(
                data=json.dumps(asdict(snapshot)),
                created_at=datetime.now(UTC),
            )

    @staticmethod
    def _process_market_data(results: dict) -> PendleMarketSnapshot:
        """Process raw market data into a structured snapshot"""

        # Create market list
        markets = [
            PendleMarketData(
                symbol=symbol,
                isNewPool=is_new,
                protocol=protocol,
                liquidityChange24h=liquidity,
                impliedApyChange24h=apy,
            )
            for symbol, is_new, protocol, liquidity, apy in zip(
                results["symbolList"],
                results["isNewList"],
                results["protocolList"],
                results["liquidityChange24hList"],
                results["impliedApyChange24hList"],
            )
        ]

        # Split the markets into new and existing
        new_markets = [market for market in markets if market.isNewPool]
        existing_markets = [market for market in markets if not market.isNewPool]

        # Sort markets by liquidity and APY increases
        liquidity_increase = nlargest(
            3, existing_markets, key=lambda x: x.liquidityChange24h
        )
        new_market_liquidity_increase = nlargest(
            3, new_markets, key=lambda x: x.liquidityChange24h
        )
        apy_increase = nlargest(
            3, existing_markets, key=lambda x: x.impliedApyChange24h
        )
        new_market_apy_increase = nlargest(
            3, new_markets, key=lambda x: x.impliedApyChange24h
        )

        # Extract symbols from sorted markets in one step
        liquidity_increase_top_symbols = {
            market.symbol for market in liquidity_increase
        }
        new_market_liquidity_increase_symbols = {
            market.symbol for market in new_market_liquidity_increase
        }
        apy_increase_symbols = {market.symbol for market in apy_increase}
        new_market_apy_increase_symbols = {
            market.symbol for market in new_market_apy_increase
        }

        # Combine all relevant symbols
        relevant_symbols = (
            liquidity_increase_top_symbols
            | new_market_liquidity_increase_symbols
            | apy_increase_symbols
            | new_market_apy_increase_symbols
        )

        # Filter markets to include only those in the relevant symbols set
        filtered_markets = [
            market for market in markets if market.symbol in relevant_symbols
        ]

        return PendleMarketSnapshot(
            markets=filtered_markets,
            liquidityIncreaseList=list(liquidity_increase_top_symbols),
            newMarketLiquidityIncreaseList=list(new_market_liquidity_increase_symbols),
            apyIncreaseList=list(apy_increase_symbols),
            newMarketApyIncreaseList=list(new_market_apy_increase_symbols),
        )
