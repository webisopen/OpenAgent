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


class TwitterQuoteConfig(BaseModel):
    debug: bool = Field(default=False, description="Enable debug mode")
    credentials: TwitterCredentials


class TwitterQuote(Tool[TwitterQuoteConfig]):
    """Tool for quoting tweets"""

    @property
    def name(self) -> str:
        return "twitter_quote"

    @property
    def description(self) -> str:
        return "Quote a tweet with additional comment"

    def __init__(self):
        super().__init__()
        self.debug = None
        self.client = None

    async def setup(self, config: TwitterQuoteConfig) -> None:
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
            logger.info("Twitter quote tool setup completed")
        except Exception as e:
            logger.error(f"Error setting up Twitter quote tool: {e}")
            raise

    async def __call__(self, tweet_id: str, comment: str) -> Any:
        """
        Quote a tweet with a comment

        Args:
            tweet_id: ID of the tweet to quote
            comment: Comment to add to the quote

        Returns:
            str: URL of the new quote tweet or error message
        """
        if not self.client:
            logger.error("Twitter client not initialized")
            raise ValueError("Twitter client not initialized. Please run setup first.")

        # check if comment is not_relevant
        if comment.lower().strip() == "not_relevant":
            logger.info(f"Skipping quote for tweet {tweet_id}: marked as not relevant")
            return "Skipped: Tweet marked as not relevant"

        logger.info(f"{self.name} tool is called for tweet: {tweet_id}")

        if self.debug:
            return f"Debug mode enabled. Skipping quote tweet: {comment} -> {tweet_id}"

        try:
            response = self.client.create_tweet(text=comment, quote_tweet_id=tweet_id)
            if response.data:
                tweet_id = response.data["id"]
                logger.info(f"Successfully quoted tweet with ID: {tweet_id}")
                return f"Successfully quoted tweet: https://twitter.com/i/web/status/{tweet_id}"
            else:
                logger.error("Failed to quote tweet: No response data")
                return "Failed to quote tweet: No response data"
        except Exception as e:
            error_msg = f"Failed to quote tweet: {str(e)}"
            logger.error(error_msg)
            return error_msg
