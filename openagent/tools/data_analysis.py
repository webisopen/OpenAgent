from typing import Any, Dict

from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from openagent.core.tool import Tool
from langchain.chat_models import init_chat_model

class DataAnalysisConfig(BaseModel):
    """Configuration for data analysis tool"""
    llm: Dict[str, Any]
    
class DataAnalysisTool(Tool):
    """Tool for analyzing data changes using LLM"""
    
    def __init__(self):
        super().__init__()
        self.chain = None
        
    @property
    def name(self) -> str:
        return "analyze_data"
        
    @property 
    def description(self) -> str:
        return "Analyzes changes and patterns in data based on provided description and data content"

    async def setup(self, config: DataAnalysisConfig) -> None:
        """Setup the analysis tool with LLM chain"""
        # Initialize LLM
        llm = init_chat_model(
            model=config.llm["model"],
            model_provider=config.llm["provider"],
            temperature=config.llm["temperature"]
        )
        
        # Create prompt template
        template = """
        You are a data analysis expert. Analyze the following data and provide insights based on the given description.
        
        Description: {description}
        
        Current Data: {current_data}
        
        Previous Data: {previous_data}
        
        Please provide a detailed analysis including:
        1. Key changes and patterns identified
        2. Notable trends
        3. Potential implications
        4. Any anomalies or points of interest
        
        Analysis:
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["description", "current_data", "previous_data"]
        )
        
        # Create LLM chain
        self.chain = LLMChain(llm=llm, prompt=prompt)

    async def __call__(self, description: str, current_data: str, previous_data) -> str:
        """
        Analyze data using LLM
        
        Args:
            description (str): Description of what to analyze in the data
            current_data (str): Current data content
            previous_data (str): Previous data content
            
        Returns:
            str: Analysis results from the LLM
        """
        if not self.chain:
            raise RuntimeError("Tool not properly initialized. Call setup() first.")
            
        try:
            # Run analysis chain
            response = await self.chain.arun(
                description=description,
                current_data=current_data,
                previous_data=previous_data
            )
            return response.strip()
            
        except Exception as e:
            error_msg = f"Error analyzing data: {str(e)}"
            return error_msg