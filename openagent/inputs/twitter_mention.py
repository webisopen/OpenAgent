import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator
import tweepy
from loguru import logger
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel

from openagent.core.input import Input, InputMessage

Base = declarative_base()


class ProcessedMention(Base):
    __tablename__ = "processed_mentions"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(String, unique=True)
    author_id = Column(String)
    processed_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)


class TwitterCredentials(BaseModel):
    bearer_token: str
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str


class TwitterMentionConfig(BaseModel):
    credentials: TwitterCredentials
    polling_interval: int = 60


class TwitterMentionInput(Input[TwitterMentionConfig]):
    def __init__(self):
        super().__init__()
        self.client = None
        self.polling_interval = 60
        self.engine = create_engine("sqlite:///storage/mentions.db")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    async def setup(self, config: TwitterMentionConfig) -> None:
        """Setup Twitter API client for mentions"""
        # Initialize Twitter API v2 client
        self.client = tweepy.Client(
            bearer_token=config.credentials.bearer_token,
            consumer_key=config.credentials.api_key,
            consumer_secret=config.credentials.api_secret,
            access_token=config.credentials.access_token,
            access_token_secret=config.credentials.access_token_secret,
        )

        # Setup configuration
        self.polling_interval = config.polling_interval
        logger.info(
            f"Twitter mention input setup for @{self.client.get_me().data.username} completed"
        )

    def is_processed(self, tweet_id: str) -> bool:
        """Check if a tweet has been processed before"""
        return (
            self.session.query(ProcessedMention)
            .filter_by(tweet_id=str(tweet_id))
            .first()
            is not None
        )

    def mark_as_processed(self, tweet_id: str, author_id: str) -> None:
        """Mark a tweet as processed"""
        mention = ProcessedMention(
            tweet_id=str(tweet_id), author_id=str(author_id), is_processed=True
        )
        self.session.add(mention)
        self.session.commit()

    async def listen(self) -> AsyncIterator[str]:
        """Listen for Twitter mentions"""
        while True:
            try:
                logger.debug("Fetching Twitter mentions...")
                start_time = datetime.now(timezone.utc) - timedelta(minutes=15)
                # Get mentions using v2 API
                response = self.client.get_users_mentions(
                    self.client.get_me().data.id,
                    tweet_fields=[
                        "created_at",
                        "text",
                        "author_id",
                        "entities",
                        "referenced_tweets",
                        "in_reply_to_user_id",
                        "conversation_id",
                    ],
                    start_time=start_time,
                )

                # reverse response.data
                if response.data:
                    for tweet in response.data:
                        # Skip if already processed
                        if self.is_processed(tweet.id):
                            logger.debug(f"Tweet {tweet.id} already processed")
                            continue

                        # Store tweet id and author id in context
                        self.context = {
                            "tweet_id": tweet.id,
                            "author_id": tweet.author_id,
                            "mark_as_processed": lambda: self.mark_as_processed(
                                tweet.id, tweet.author_id
                            ),
                        }

                        yield InputMessage(
                            session_id=str(tweet.author_id),
                            message=tweet.text,
                        )

            except Exception as e:
                logger.error(f"Error fetching Twitter mentions: {e}")

            await asyncio.sleep(self.polling_interval)
