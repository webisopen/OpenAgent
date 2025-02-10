from typing import Optional
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from openagent.core.tool import Tool

class DataAnalysisConfig(BaseModel):
    """Configuration for data analysis tool"""
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    api_key: Optional[str] = None

class DataAnalysisTool(Tool):
    """Tool for analyzing data changes using LLM"""
    
    def __init__(self):
        super().__init__()
        self.llm = None
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
        self.llm = ChatOpenAI(
            model_name=config.model_name,
            temperature=config.temperature,
            openai_api_key=config.api_key
        )
        
        # Create prompt template
        template = """
        You are a data analysis expert. Analyze the following data and provide insights based on the given description.
        
        Description: {description}
        
        Data: {data}
        
        Please provide a detailed analysis including:
        1. Key changes and patterns identified
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
        self.chain = LLMChain(llm=self.llm, prompt=prompt)

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