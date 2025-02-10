import tweepy
from loguru import logger
from pydantic import BaseModel

from openagent.core.io.output import Output


class TwitterCredentials(BaseModel):
    bearer_token: str
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str


class TwitterPostConfig(BaseModel):
    credentials: TwitterCredentials


class TwitterPostOutput(Output[TwitterPostConfig]):
    def __init__(self):
        super().__init__()
        self.client = None

    async def setup(self, config: TwitterPostConfig) -> None:
        """Setup Twitter API client"""
        try:
            # Initialize Twitter API v2 client with both OAuth 1.0a and Bearer token
            self.client = tweepy.Client(
                bearer_token=config.credentials.bearer_token,
                consumer_key=config.credentials.api_key,
                consumer_secret=config.credentials.api_secret,
                access_token=config.credentials.access_token,
                access_token_secret=config.credentials.access_token_secret,
            )
            logger.info("Twitter post output setup completed")
        except Exception as e:
            logger.error(f"Error setting up Twitter post output: {e}")
            raise

    async def send(self, message: str) -> bool:
        """Post a tweet"""
        try:
            # Create the tweet
            response = self.client.create_tweet(text=message)

            if response.data:
                tweet_id = response.data["id"]
                logger.info(f"Successfully posted tweet with ID: {tweet_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False
