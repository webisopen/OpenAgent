import asyncio
from typing import AsyncIterator, Dict, Any
from loguru import logger

from openagent.core.input import Input


class StdinInput(Input):
    def __init__(self):
        self.prompt = "> "
    
    async def setup(self, config: Dict[str, Any]) -> None:
        """Setup stdin input configuration"""
        self.prompt = config.get('prompt', '> ')
    
    async def listen(self) -> AsyncIterator[str]:
        """Listen for stdin input"""
        while True:
            try:
                # Use asyncio.get_event_loop().run_in_executor to make input non-blocking
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(None, input, self.prompt)
                
                if user_input.strip():  # Only yield non-empty input
                    yield user_input
                
            except Exception as e:
                logger.error(f"Error reading stdin input: {e}")
            
            await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging 