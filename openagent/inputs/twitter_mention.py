import os
import asyncio
from datetime import datetime, timedelta
from typing import AsyncIterator, Dict, Any
import tweepy
from loguru import logger

from openagent.core.input import Input


class TwitterMentionInput(Input):
    def __init__(self):
        self.client = None
        self.polling_interval = 60
        self.last_mention_id = None

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

    async def listen(self) -> AsyncIterator[str]:
        """Listen for Twitter mentions"""
        while True:
            try:
                last_1_hour = datetime.now() - timedelta(hours=1)
                # Get mentions using v2 API
                response = self.client.get_users_mentions(
                    self.client.get_me().data.id,
                    since_id=self.last_mention_id,
                    tweet_fields=['text'],
                    start_time=last_1_hour
                )

                if response.data:
                    for tweet in response.data:
                        self.last_mention_id = max(tweet.id if self.last_mention_id is None else self.last_mention_id,
                                                   tweet.id)
                        yield tweet.text

            except Exception as e:
                logger.error(f"Error fetching Twitter mentions: {e}")

            await asyncio.sleep(self.polling_interval)
