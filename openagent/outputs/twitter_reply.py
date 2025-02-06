from typing import Dict, Any
from loguru import logger
import tweepy

from openagent.core.output import Output


class TwitterReplyOutput(Output):
    def __init__(self):
        super().__init__()  # Initialize the base class context
        self.client = None
        
    async def setup(self, config: Dict[str, Any]) -> None:
        """Setup Twitter API client with credentials"""
        try:
            credentials = config.get('credentials', {})
            self.client = tweepy.Client(
                bearer_token=credentials.get('bearer_token'),
                consumer_key=credentials.get('api_key'),
                consumer_secret=credentials.get('api_secret'),
                access_token=credentials.get('access_token'),
                access_token_secret=credentials.get('access_token_secret')
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
            tweet_id = self.context.get('tweet_id')
            
            if tweet_id:
                self.client.create_tweet(
                    text=message,
                    in_reply_to_tweet_id=tweet_id,
                )
                return True
            else:
                logger.error("Missing tweet_id in context")
                return False
                
        except Exception as e:
            logger.error(f"Error sending tweet: {e}")
            return False 