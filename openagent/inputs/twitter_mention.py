import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, Any
import tweepy
from loguru import logger

from openagent.core.input import Input


class TwitterMentionInput(Input):
    def __init__(self):
        super().__init__()  # Initialize the base class context
        self.client = None
        self.polling_interval = 60
        self.last_mention_id = 141

    async def setup(self, config: Dict[str, Any]) -> None:
        """Setup Twitter API client for mentions"""
        credentials = config.get('credentials', {})

        # Initialize Twitter API v2 client
        self.client = tweepy.Client(
            bearer_token=credentials.get('bearer_token'),
            consumer_key=credentials.get('api_key'),
            consumer_secret=credentials.get('api_secret'),
            access_token=credentials.get('access_token'),
            access_token_secret=credentials.get('access_token_secret')
        )

        # Setup configuration
        self.polling_interval = config.get('polling_interval', 60)
        logger.info(f"Twitter mention input setup for @{self.client.get_me().data.username} completed")

    async def listen(self) -> AsyncIterator[str]:
        """Listen for Twitter mentions"""
        while True:
            try:
                logger.debug("Fetching Twitter mentions...")
                last_1_hours = datetime.now(timezone.utc) - timedelta(hours=1)
                # Get mentions using v2 API
                response = self.client.get_users_mentions(
                    self.client.get_me().data.id,
                    tweet_fields=["created_at",
                                  "text",
                                  "author_id",
                                  "entities",
                                  "referenced_tweets",
                                  "in_reply_to_user_id",
                                  "conversation_id"],
                    start_time=last_1_hours
                )

                # reverse response.data
                if response.data:
                    for tweet in response.data:
                        self.last_mention_id = tweet.id
                        # Store tweet id and author id in context
                        self.context = {
                            'tweet_id': tweet.id,
                            'author_id': tweet.author_id
                        }
                        yield tweet.text

            except Exception as e:
                logger.error(f"Error fetching Twitter mentions: {e}")

            await asyncio.sleep(self.polling_interval)
