from typing import Dict, Any
from loguru import logger

from openagent.core.output import Output


class StdoutOutput(Output):
    def __init__(self):
        self.prefix = ""
        self.use_colors = True

    async def setup(self, config: Dict[str, Any]) -> None:
        """Setup stdout output configuration"""
        self.prefix = config.get("prefix", "")
        self.use_colors = config.get("use_colors", True)

    async def send(self, message: str) -> bool:
        """Print message to stdout"""
        try:
            if self.use_colors:
                # Use cyan color for output
                formatted_message = f"\033[96m{self.prefix}{message}\033[0m"
            else:
                formatted_message = f"{self.prefix}{message}"

            print(formatted_message)
            return True

        except Exception as e:
            logger.error(f"Error printing to stdout: {e}")
            return False
