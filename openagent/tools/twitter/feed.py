from typing import Optional, List

from loguru import logger
from pydantic import BaseModel
import httpx
from datetime import datetime, timedelta, UTC
import re
import asyncio

from openagent.core.tool import Tool


class Tweet(BaseModel):
    """Model representing a tweet"""

    tweet_id: str
    handle: str
    content: str
    created_at: datetime
    type: str


class TwitterFeedConfig(BaseModel):
    """Configuration for the Twitter feed function"""

    handles: list[str]  # List of Twitter handles to fetch tweets from
    limit: int = 50  # Default number of tweets to return per handle
    tweet_type: Optional[str] = (
        None  # Optional filter for tweet type (tweet, reply, retweet, quote)
    )
    time_filter: Optional[str] = (
        None  # Time filter in format like "10min", "1hour", "24hour"
    )

    @property
    def time_threshold(self) -> Optional[datetime]:
        """Convert time filter string to datetime threshold"""
        if not self.time_filter:
            return None

        pattern = r"(\d+)(min|hour)"
        match = re.match(pattern, self.time_filter)
        if not match:
            return None

        value, unit = match.groups()
        value = int(value)

        now = datetime.now(UTC)  # Already UTC aware
        if unit == "min":
            return now - timedelta(minutes=value)
        elif unit == "hour":
            return now - timedelta(hours=value)
        return None


class GetTwitterFeed(Tool[TwitterFeedConfig]):
    """Function to get tweets from a Twitter handle using RSS3 API"""

    def __init__(self):
        super().__init__()
        self.config: TwitterFeedConfig | None = None
        self.base_url = "https://ai.rss3.io/api/v1/tweets"
        self.max_retries = 5
        self.retry_delay = 1

    @property
    def name(self) -> str:
        return "get_twitter_feed"

    @property
    def description(self) -> str:
        return "Get recent tweets from specified Twitter handles with optional time filtering"

    async def setup(self, config: TwitterFeedConfig) -> None:
        """Setup the function with configuration"""
        self.config = config

    async def _fetch_single_handle(
        self, client: httpx.AsyncClient, handle: str
    ) -> List[dict]:
        """Fetch tweets for a single handle with retry logic"""
        params = {"limit": self.config.limit if self.config else 50}
        if self.config and self.config.tweet_type:
            params["type"] = self.config.tweet_type

        for retry_count in range(self.max_retries):
            try:
                logger.info(f"Fetching tweets for @{handle}")
                response = await client.get(f"{self.base_url}/{handle}", params=params)

                if response.status_code != 200:
                    if retry_count < self.max_retries - 1:
                        logger.error(
                            f"HTTP {response.status_code}, retrying {retry_count + 2}/{self.max_retries}"
                        )
                        await asyncio.sleep(self.retry_delay)
                        continue
                    logger.error(
                        f"Failed after {self.max_retries} attempts: HTTP {response.status_code}"
                    )
                    return []

                tweets = response.json() or []
                if not tweets:
                    logger.info(f"No tweets found for @{handle}")
                return tweets

            except Exception as e:
                if retry_count < self.max_retries - 1:
                    logger.error(
                        f"Error (attempt {retry_count + 1}/{self.max_retries}): {str(e)}"
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed after {self.max_retries} attempts: {str(e)}")
                    return []

        return []

    def _apply_time_filter(self, tweets: List[dict]) -> List[dict]:
        """Filter tweets based on time threshold"""
        if not self.config or not self.config.time_threshold:
            return tweets

        filtered = []
        for tweet in tweets:
            tweet_time = datetime.fromisoformat(tweet["created_at"]).replace(tzinfo=UTC)
            if tweet_time >= self.config.time_threshold:
                filtered.append(tweet)

        if not filtered:
            logger.info("No tweets found after applying time filter")

        return filtered

    def _format_output(self, tweets: List[Tweet]) -> str:
        """Format tweets into readable output"""
        if not tweets:
            return "No tweets found matching the criteria."

        tweets.sort(key=lambda x: x.created_at, reverse=True)
        formatted = []

        for tweet in tweets:
            created_at = tweet.created_at.strftime("%Y-%m-%d %H:%M:%S")
            formatted.append(
                f"TWEET_ID={tweet.tweet_id}||"
                f"@{tweet.handle} [{created_at}] {tweet.type.upper()}: {tweet.content}"
            )

        return "\n\n".join(formatted)

    async def __call__(self) -> str:
        """Main function to get tweets from all configured handles"""
        logger.info(f"{self.name} tool is called with config: {self.config}")
        all_tweets = []

        async with httpx.AsyncClient() as client:
            for handle in self.config.handles:
                # Fetch and filter tweets
                raw_tweets = await self._fetch_single_handle(client, handle)
                filtered_tweets = self._apply_time_filter(raw_tweets)

                # Convert to Tweet objects
                for tweet in filtered_tweets:
                    all_tweets.append(Tweet(**tweet))

        result = self._format_output(all_tweets)
        logger.info(f"Final output:\n{result}")
        return result
