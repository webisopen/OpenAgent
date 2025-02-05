import asyncio
from typing import Dict, Any
import tweepy
from loguru import logger

from openagent.core.output import Output


class TwitterOutput(Output):
    def __init__(self):
        self.api = None
        self.max_length = 280
        self.thread_enabled = True
        self.signature = ""
        self.rate_limit = 300
        self.retry_attempts = 3
        self.retry_delay = 5
    
    async def setup(self, config: Dict[str, Any]) -> None:
        """Setup Twitter API client"""
        credentials = config.get('credentials', {})
        
        # Initialize Twitter API
        auth = tweepy.OAuthHandler(
            credentials.get('api_key'),
            credentials.get('api_secret')
        )
        auth.set_access_token(
            credentials.get('access_token'),
            credentials.get('access_token_secret')
        )
        self.api = tweepy.API(auth)
        
        # Setup configuration
        self.max_length = config.get('max_length', 280)
        self.thread_enabled = config.get('thread_enabled', True)
        self.signature = config.get('signature', '')
        self.rate_limit = config.get('rate_limit', 300)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 5)
    
    def _split_message(self, message: str) -> list[str]:
        """Split message into multiple tweets if needed"""
        if len(message) <= self.max_length:
            return [message]
        
        parts = []
        current_part = ""
        words = message.split()
        
        for word in words:
            if len(current_part) + len(word) + 1 <= self.max_length - len(self.signature):
                current_part += (" " + word if current_part else word)
            else:
                parts.append(current_part + self.signature)
                current_part = word
        
        if current_part:
            parts.append(current_part + self.signature)
        
        return parts
    
    async def send(self, message: str) -> bool:
        """Send message as tweet or thread"""
        parts = self._split_message(message)
        
        try:
            previous_tweet = None
            for part in parts:
                for attempt in range(self.retry_attempts):
                    try:
                        if previous_tweet and self.thread_enabled:
                            tweet = self.api.update_status(
                                status=part,
                                in_reply_to_status_id=previous_tweet.id
                            )
                        else:
                            tweet = self.api.update_status(status=part)
                        
                        previous_tweet = tweet
                        break
                    except Exception as e:
                        if attempt == self.retry_attempts - 1:
                            raise e
                        await asyncio.sleep(self.retry_delay)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending tweet: {e}")
            return False 