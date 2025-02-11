from textwrap import dedent
from typing import Any, Dict

from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from openagent.core.tool import Tool
from langchain.chat_models import init_chat_model

class PendleMarketAnalysisConfig(BaseModel):
    """Configuration for data analysis tool"""
    llm: Dict[str, Any]
    
class PendleMarketAnalysisTool(Tool):
    """Tool for analyzing data changes using LLM"""
    
    def __init__(self):
        super().__init__()
        self.chain = None
        
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
            model=config.llm["model"],
            model_provider=config.llm["provider"],
            temperature=config.llm["temperature"]
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

        Analysis:
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["description", "data"]
        )
        
        # Create LLM chain
        self.chain = LLMChain(llm=llm, prompt=prompt)

    async def __call__(self, description: str, data: str) -> str:
        """
        Analyze data using LLM
        
        Args:
            description (str): Description of what to analyze in the data
			data (str): The data content to analyze
            
        Returns:
            str: Analysis results from the LLM
        """
        if not self.chain:
            raise RuntimeError("Tool not properly initialized. Call setup() first.")
            
        try:
            # Run analysis chain
            response = await self.chain.arun(
                description=description,
                data=data
            )
            return response.strip()
            
        except Exception as e:
            error_msg = f"Error analyzing data: {str(e)}"
            return error_msg