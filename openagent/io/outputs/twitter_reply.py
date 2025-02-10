from loguru import logger
import tweepy
from pydantic import BaseModel

from openagent.core.io.output import Output


class TwitterCredentials(BaseModel):
    bearer_token: str
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str


class TwitterReplyConfig(BaseModel):
    credentials: TwitterCredentials


class TwitterReplyOutput(Output[TwitterReplyConfig]):
    def __init__(self):
        super().__init__()
        self.client = None

    async def setup(self, config: TwitterReplyConfig) -> None:
        """Setup Twitter API client with credentials"""
        try:
            self.client = tweepy.Client(
                bearer_token=config.credentials.bearer_token,
                consumer_key=config.credentials.api_key,
                consumer_secret=config.credentials.api_secret,
                access_token=config.credentials.access_token,
                access_token_secret=config.credentials.access_token_secret,
            )

        except Exception as e:
            logger.error(f"Error setting up Twitter client: {e}")
            raise

    async def send(self, message: str) -> bool:
        """Send reply tweet"""
        if not self.client:
            logger.error("Twitter client not initialized")
            return False

        try:
            # Get tweet ID from context
            tweet_id = self.context.get("tweet_id")

            if tweet_id:
                self.client.create_tweet(
                    text=message,
                    in_reply_to_tweet_id=tweet_id,
                )
                # Mark the tweet as processed after successful reply
                mark_as_processed = self.context.get("mark_as_processed")
                if mark_as_processed:
                    mark_as_processed()
                return True
            else:
                logger.error("Missing tweet_id in context")
                return False

        except Exception as e:
            logger.error(f"Error sending tweet: {e}")
            return False
