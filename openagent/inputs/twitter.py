import os
import asyncio
from typing import AsyncIterator, Dict, Any
import tweepy
from loguru import logger

from openagent.core.input import Input


class TwitterInput(Input):
    def __init__(self):
        self.api = None
        self.polling_interval = 60
        self.rate_limit = 100
        self.filters = []
        self.last_id = None
    
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
        self.polling_interval = config.get('polling_interval', 60)
        self.rate_limit = config.get('rate_limit', 100)
        self.filters = config.get('filters', [])
    
    def _apply_filters(self, text: str) -> bool:
        """Apply content filters to text"""
        for filter_config in self.filters:
            if filter_config['type'] == 'content_contains':
                if not any(value.lower() in text.lower() for value in filter_config['values']):
                    return False
        return True
    
    async def listen(self) -> AsyncIterator[str]:
        """Listen for Twitter mentions and DMs"""
        while True:
            try:
                # Get mentions
                mentions = self.api.mentions_timeline(since_id=self.last_id)
                for mention in mentions:
                    if self._apply_filters(mention.text):
                        self.last_id = max(mention.id if self.last_id is None else self.last_id, mention.id)
                        yield mention.text
                
                # Get direct messages
                messages = self.api.get_direct_messages()
                for message in messages:
                    if self._apply_filters(message.message_create['message_data']['text']):
                        yield message.message_create['message_data']['text']
                
            except Exception as e:
                logger.error(f"Error fetching Twitter updates: {e}")
            
            await asyncio.sleep(self.polling_interval) 