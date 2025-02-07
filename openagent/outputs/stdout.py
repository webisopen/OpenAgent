from loguru import logger
from pydantic import BaseModel

from openagent.core.interfaces.output import Output


class StdoutConfig(BaseModel):
    prefix: str = ""
    use_colors: bool = True


class StdoutOutput(Output[StdoutConfig]):
    def __init__(self):
        super().__init__()
        self.prefix = ""
        self.use_colors = True

    async def setup(self, config: StdoutConfig) -> None:
        """Setup stdout output configuration"""
        self.prefix = config.prefix
        self.use_colors = config.use_colors

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
