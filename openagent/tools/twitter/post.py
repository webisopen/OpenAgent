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


class TwitterToolConfig(BaseModel):
    debug: bool = Field(default=False, description="Enable debug mode")
    credentials: TwitterCredentials


class TwitterPostTool(Tool[TwitterToolConfig]):
    """Tool for posting tweets using Twitter API."""

    @property
    def name(self) -> str:
        return "twitter_post"

    @property
    def description(self) -> str:
        return "Use this tool to post tweets to Twitter"

    def __init__(self):
        super().__init__()
        self.debug = None
        self.client = None

    async def setup(self, config: TwitterToolConfig) -> None:
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
            logger.info("Twitter post tool setup completed")
        except Exception as e:
            logger.error(f"Error setting up Twitter post tool: {e}")
            raise

    async def __call__(self, text: str) -> Any:
        """Execute the Twitter tool to post a tweet
        @type text: the text content of the tweet to post
        """
        if not self.client:
            logger.error("Twitter client not initialized")
            raise ValueError("Twitter client not initialized. Please run setup first.")
        return await self.post_tweet(text, self.client)

    async def post_tweet(self, text: str, client: tweepy.Client) -> str:
        logger.info(f"{self.name} tool is called with text: {text}")
        """Post a tweet using tweepy client"""
        if self.debug:
            return f"Debug mode enabled. Skipping tweet post: {text}"

        try:
            response = client.create_tweet(text=text)
            if response.data:
                tweet_id = response.data["id"]
                logger.info(f"Successfully posted tweet with ID: {tweet_id}")
                return f"Tweet posted successfully. Tweet ID: {tweet_id}"
            else:
                logger.error("Failed to post tweet: No response data")
                return "Failed to post tweet: No response data"
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return f"Error posting tweet: {str(e)}"
