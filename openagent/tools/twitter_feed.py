from typing import List, Optional
from pydantic import BaseModel
import aiohttp
from datetime import datetime, timedelta, UTC
import re

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

    limit: int = 50  # Default number of tweets to return
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

        now = datetime.now(UTC)
        if unit == "min":
            return now - timedelta(minutes=value)
        elif unit == "hour":
            return now - timedelta(hours=value)
        return None


class GetTwitterFeed(Tool[TwitterFeedConfig]):
    """Function to get tweets from a Twitter handle using RSS3 API"""

    @property
    def name(self) -> str:
        return "get_twitter_feed"

    @property
    def description(self) -> str:
        return "Get recent tweets from a specified Twitter handle with optional time filtering"

    def __init__(self):
        super().__init__()
        self.config: TwitterFeedConfig | None = None
        self.base_url = "https://ai.rss3.io/api/v1/tweets"

    async def setup(self, config: TwitterFeedConfig) -> None:
        """Setup the function with configuration"""
        self.config = config

    async def __call__(self, handle: str) -> str:
        """Get recent tweets from a specified Twitter handle.

        Args:
            handle (str): The Twitter handle (without @ symbol)

        Returns:
            str: A formatted string containing the tweets or error message
        """
        try:
            params = {"limit": self.config.limit if self.config else 50}
            if self.config and self.config.tweet_type:
                params["type"] = self.config.tweet_type

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/{handle}", params=params
                ) as response:
                    if response.status != 200:
                        return f"Error fetching tweets for @{handle}: HTTP {response.status}"

                    tweets = await response.json()
                    if not tweets:
                        return f"No tweets found for @{handle}"

                    # Apply time filter if configured
                    time_threshold = self.config.time_threshold if self.config else None
                    if time_threshold:
                        filtered_tweets = []
                        for tweet in tweets:
                            tweet_time = datetime.fromisoformat(
                                tweet["created_at"].replace("Z", "+00:00")
                            )
                            if tweet_time >= time_threshold:
                                filtered_tweets.append(tweet)
                        tweets = filtered_tweets

                        if not tweets:
                            return f"No tweets found for @{handle} in the last {self.config.time_filter}"

                    # Format the tweets into a readable string
                    formatted_tweets = []
                    for tweet in tweets:
                        tweet_obj = Tweet(**tweet)
                        created_at = tweet_obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        formatted_tweets.append(
                            f"[{created_at}] {tweet_obj.type.upper()}: {tweet_obj.content}"
                        )

                    return "\n\n".join(formatted_tweets)

        except Exception as e:
            return f"Error fetching tweets for @{handle}: {str(e)}"
