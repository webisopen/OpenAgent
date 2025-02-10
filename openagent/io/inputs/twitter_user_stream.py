import asyncio
import threading
from typing import AsyncIterator, List

import tweepy
from loguru import logger
from pydantic import BaseModel

from openagent.core.io.input import Input, InputMessage


class TwitterCredentials(BaseModel):
    bearer_token: str


class TwitterUserStreamConfig(BaseModel):
    credentials: TwitterCredentials
    usernames: List[str]  # List of usernames to monitor


class TweetStreamListener(tweepy.StreamingClient):
    def __init__(self, bearer_token, callback, loop):
        super().__init__(bearer_token)
        self.callback = callback
        self.loop = loop

    def on_tweet(self, tweet):
        """Handle incoming tweets"""
        try:
            logger.info(f"Received tweet: {tweet.text}")
            future = asyncio.run_coroutine_threadsafe(
                self.callback(tweet),
                self.loop
            )
            future.result()  # Wait for the coroutine to complete
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")

    def on_error(self, status):
        logger.error(f"Stream error: {status}")
        if status == 420:  # Rate limit error
            return False
        return True

    def on_connection_error(self):
        logger.error("Connection error occurred")
        return True


class TwitterUserStreamInput(Input[TwitterUserStreamConfig]):
    def __init__(self):
        super().__init__()
        self.client = None
        self.stream = None
        self.tweet_queue = asyncio.Queue()
        self.usernames = []
        self.user_ids = []
        self._running = True
        self.loop = None
        self.stream_thread = None

    async def setup(self, config: TwitterUserStreamConfig) -> None:
        """Setup Twitter API client and stream"""
        self.loop = asyncio.get_running_loop()

        # Initialize Twitter API v2 client
        self.client = tweepy.Client(
            bearer_token=config.credentials.bearer_token
        )

        self.usernames = config.usernames

        # Get user IDs for the usernames
        for username in self.usernames:
            try:
                user = self.client.get_user(username=username)
                if user.data:
                    self.user_ids.append(str(user.data.id))
                    logger.info(f"Found user ID for {username}: {user.data.id}")
            except Exception as e:
                logger.error(f"Error getting user ID for {username}: {e}")

        # Initialize stream
        self.stream = TweetStreamListener(
            config.credentials.bearer_token,
            self._process_tweet,
            self.loop
        )

        # Clear existing rules
        existing_rules = self.stream.get_rules()
        if existing_rules.data:
            rule_ids = [rule.id for rule in existing_rules.data]
            self.stream.delete_rules(rule_ids)

        # Add monitoring rules for each user
        for user_id in self.user_ids:
            rule = f"from:{user_id}"
            self.stream.add_rules(tweepy.StreamRule(rule))

        # Start stream in a separate thread
        self.stream_thread = threading.Thread(target=self._start_stream)
        self.stream_thread.daemon = True
        self.stream_thread.start()

        logger.info(f"Twitter user stream setup completed for users: {', '.join(self.usernames)}")

    async def _process_tweet(self, tweet):
        """Process incoming tweets and add them to the queue"""
        try:
            self.context = {
                "tweet_id": tweet.id,
                "author_id": tweet.author_id,
            }
            logger.info(f"Processing tweet: {tweet.text}")
            await self.tweet_queue.put(
                InputMessage(
                    session_id=str(tweet.author_id),
                    message=tweet.text,
                )
            )
        except Exception as e:
            logger.error(f"Error in _process_tweet: {e}")

    def _start_stream(self):
        """Start the Twitter stream in a separate thread"""
        try:
            logger.info("Starting Twitter stream...")
            self.stream.filter(
                tweet_fields=['created_at', 'author_id', 'public_metrics'],
                expansions=['author_id']
            )
        except Exception as e:
            logger.error(f"Error in _start_stream: {e}")

    async def listen(self) -> AsyncIterator[InputMessage]:
        """Listen for Twitter posts from specified users"""
        logger.info("Starting to listen for tweets...")
        while self._running:
            try:
                # Wait for new tweets from the queue with a timeout
                message = await asyncio.wait_for(self.tweet_queue.get(), timeout=1.0)
                yield message
                self.tweet_queue.task_done()
            except asyncio.TimeoutError:
                continue  # Continue listening if timeout occurs
            except Exception as e:
                logger.error(f"Error in Twitter stream listener: {e}")
                await asyncio.sleep(5)  # Wait before retrying
