import os

import tweepy
from dotenv import load_dotenv

load_dotenv()


class TwitterHandler:
    def __init__(self):
        self.client = None
        self.initialize_client()

    def initialize_client(self):
        """Initialize Twitter client with credentials from environment variables."""
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
                consumer_key=os.getenv("TWITTER_API_KEY"),
                consumer_secret=os.getenv("TWITTER_API_SECRET"),
                access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Twitter client: {e!s}") from e

    def post_tweet(self, content: str) -> tuple[bool, str]:
        """
        Post a tweet using the initialized client.

        Args:
            content (str): The content to tweet
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not self.client:
                self.initialize_client()

            response = self.client.create_tweet(text=content)
            return True, f"Tweet posted successfully. Tweet ID: {response.data['id']}"
        except Exception as e:
            return False, str(e)
