from openagent.cli import cli
from loguru import logger

if __name__ == "__main__":
    try:
        cli(["start", "--file", "twitter_agent.yaml"])
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        raise
