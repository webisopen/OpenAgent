import json
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import aiohttp
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from openagent.agent.config import ModelConfig
from openagent.core.tool import Tool
from langchain.chat_models import init_chat_model

Base = declarative_base()

POOL_VOTER_APY_CONFIG = {
    "url": "https://api-v2.pendle.finance/bff/v1/ve-pendle/pool-voter-apy",
    "description": 
        """
        Pendle Market APY API provides APY information for Pendle markets across different chains and protocols.
        Response Structure:
            top_apy_changes:
                Array of pools with highest APY increases, containing:
                - poolId:            Unique identifier for the pool
                - name:              Pool name
                - symbol:            Pool token symbol
                - address:          Pool contract address
                - protocol:         Protocol name
                - voterApy:         Current voter APY value
                - lastEpochVoterApy: Previous epoch voter APY
                - lastEpochChange:   APY change from last epoch (sorted by this field)
            bottom_apy_changes:
                Array of pools with highest APY decreases
                (Same structure as top_apy_changes) 
            totalPools:   Total number of pools available
            timestamp:    Date timestamp
        """
}

class PendleMarketData(Base):
    __tablename__ = "pendle_market_data"

    id = Column(Integer, primary_key=True)
    uri = Column(String) # api endpoint
    data = Column(String) # json response
    created_at = Column(DateTime, default=datetime.utcnow)

class PendleMarketAnalysisConfig(BaseModel):
    """Configuration for data analysis tool"""
    model: ModelConfig

class PendleMarketAnalysisTool(Tool):
    """Tool for analyzing data changes using LLM"""
    
    def __init__(self):
        super().__init__()
        self.chain = None
        self.engine = create_engine("sqlite:///storage/pendle_market_analysis.db")
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()
        
    @property
    def name(self) -> str:
        return "pendle_market_analysis"
        
    @property 
    def description(self) -> str:
        return """You are a DeFi data analysis expert.
        You receive the latest data from Pendle Finance in JSON and provide a structured analysis report.
        """

    async def setup(self, config: PendleMarketAnalysisConfig) -> None:
        """Setup the analysis tool with LLM chain"""
        # Initialize LLM
        llm = init_chat_model(
            model=config.model.name,
            model_provider=config.model.provider,
            temperature=config.model.termperature,
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
 
        Your analysis must include:
        1. Key changes and patterns
        2. Notable trends
        3. Potential implications
        4. Any anomalies or points of interest
        
        Your analysis should be structured and concise, do not include any long paragraphs. 

        Analysis:
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["description", "data"]
        )
        
        # Create LLM chain
        self.chain = LLMChain(llm=llm, prompt=prompt)

    async def __call__(self) -> str:
        """
        Analyze data using LLM
            
        Returns:
            str: Analysis results from the LLM
        """
        if not self.chain:
            raise RuntimeError("Tool not properly initialized. Call setup() first.")
            
        try:
            # Query existing data
            snapshot = self.session.query(PendleMarketData).order_by(PendleMarketData.created_at.desc()).first()

            # Fetch data
            result = await self._fetch_pendle_market_apy()

            # Compare with existing data
            if snapshot:
                snapshot_data = eval(snapshot.data)
                result_data = eval(result.data)
                
                if snapshot_data == result_data:
                    return "NO_NEW_DATA"
            
            # Save new data to database
            self.session.add(result)
            self.session.commit()
            
            # Run analysis chain
            response = await self.chain.arun(
                description=POOL_VOTER_APY_CONFIG["description"],
                data=result.data
            )

            return response.strip()
            
        except Exception as e:
            error_msg = f"Error analyzing data: {str(e)}"
            return error_msg

    async def _fetch_pendle_market_apy(self) -> PendleMarketData:
        async with aiohttp.ClientSession() as session:
            async with session.request(method="GET", url=POOL_VOTER_APY_CONFIG["url"]) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")

                # Get response data
                result = await response.text()

                data = self._filter_pendle_market_apy(result)

                # Create new snapshot
                snapshot = PendleMarketData(
                    uri=POOL_VOTER_APY_CONFIG["url"],
                    data=str(data),
                    created_at=datetime.utcnow()
                )

                return snapshot
    
    def _filter_pendle_market_apy(self, response: str) -> dict:
        """Filter pool voter apy data"""
        data = json.loads(response)

        if not data.get('results'):
            return data

        def extract_pool_info(item: dict) -> dict:
            """Extract relevant pool information"""
            root_fields = ('poolId', 'voterApy', 'lastEpochVoterApy', 'lastEpochChange')
            pool_fields = ('name', 'symbol', 'address', 'protocol')

            return {
                **{k: item[k] for k in root_fields},
                **{k: item['pool'][k] for k in pool_fields}
            }

        sorted_results = sorted(
            data['results'],
            key=lambda x: x.get('lastEpochChange', 0),
            reverse=True
        )

        return {
            'top_apy_changes': [extract_pool_info(item) for item in sorted_results[:5]],
            'bottom_apy_changes': [extract_pool_info(item) for item in sorted_results[-5:]] if len(sorted_results) > 5 else [],
            'totalPools': data.get('totalPools')
        }