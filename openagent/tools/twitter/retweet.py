import tweepy
from typing import Any
from loguru import logger
from pydantic import BaseModel, Field

from openagent.core.tool import Tool


class TwitterCredentials(BaseModel):
    bearer_token: str = Field(description="Twitter API bearer token")
    api_key: str = Field(description="Twitter API key (consumer key)")
    api_secret: str = Field(description="Twitter API secret (consumer secret)")
    access_token: str = Field(description="Twitter API access token")
    access_token_secret: str = Field(description="Twitter API access token secret")


class TwitterRetweetConfig(BaseModel):
    debug: bool = Field(default=False, description="Enable debug mode")
    credentials: TwitterCredentials


class TwitterRetweet(Tool[TwitterRetweetConfig]):
    """Tool for retweeting tweets"""

    @property
    def name(self) -> str:
        return "twitter_retweet"

    @property
    def description(self) -> str:
        return "Retweet a tweet without adding a comment"

    def __init__(self):
        super().__init__()
        self.debug = None
        self.client = None

    async def setup(self, config: TwitterRetweetConfig) -> None:
        """Setup the Twitter tool with API credentials"""
        try:
            self.debug = config.debug
            self.client = tweepy.Client(
                bearer_token=config.credentials.bearer_token,
                consumer_key=config.credentials.api_key,
                consumer_secret=config.credentials.api_secret,
                access_token=config.credentials.access_token,
                access_token_secret=config.credentials.access_token_secret,
            )
            logger.info("Twitter retweet tool setup completed")
        except Exception as e:
            logger.error(f"Error setting up Twitter retweet tool: {e}")
            raise

    async def __call__(self, tweet_id: str) -> Any:
        """
        Retweet a tweet

        Args:
            tweet_id: ID of the tweet to retweet

        Returns:
            str: URL of the retweeted tweet or error message
        """
        if not self.client:
            logger.error("Twitter client not initialized")
            raise ValueError("Twitter client not initialized. Please run setup first.")

        logger.info(f"{self.name} tool is called for tweet: {tweet_id}")

        if self.debug:
            return f"Debug mode enabled. Skipping retweet: {tweet_id}"

        try:
            response = self.client.retweet(tweet_id)
            if response.data:
                logger.info(f"Successfully retweeted tweet with ID: {tweet_id}")
                return f"Successfully retweeted: https://twitter.com/i/web/status/{tweet_id}"
            else:
                logger.error("Failed to retweet: No response data")
                return "Failed to retweet: No response data"
        except Exception as e:
            error_msg = f"Failed to retweet: {str(e)}"
            logger.error(error_msg)
            return error_msg
