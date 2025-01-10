from dotenv import load_dotenv
from loguru import logger

import openagent

if __name__ == "__main__":
    load_dotenv()

    logger.info("Starting OpenAgent")

    openagent.run()
