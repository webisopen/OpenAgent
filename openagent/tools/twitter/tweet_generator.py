import logging
import os
from typing import Tuple, Optional
from phi.tools import Toolkit
from phi.model.openai import OpenAIChat
from phi.model.base import Model
from phi.model.message import Message
from dotenv import load_dotenv
from .twitter_handler import TwitterHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

SYSTEM_PROMPT = """You are a creative tweet writer who can adapt to different personalities and styles.
Your task is to generate engaging tweets that match the given personality and topic.
ALWAYS include relevant hashtags in your tweets to increase visibility and engagement.
Format your response exactly like a real human tweet - no quotes, no additional text."""

TWEET_REQUIREMENTS = """
Requirements for the tweet:
1. Keep it under 280 characters
2. Use appropriate tone and style for the given personality
3. MUST include at least 2-3 relevant hashtags
4. Make it engaging and shareable
5. Match the tone to the specified personality
6. Format exactly like a real human tweet
7. No quotes or other formatting - just the tweet text
"""


class TweetGeneratorTools(Toolkit):
    def __init__(self, model: Optional[Model] = None):
        super().__init__(name="tweet_generator_tools")
        self.twitter_handler = TwitterHandler()

        # Use provided model (from agent) or create a new one
        if model:
            self.model = model
        else:
            # Initialize OpenAI model for standalone use
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")

            # Initialize model params
            model_params = {
                "id": "gpt-4o",
                "name": "TweetGenerator",
                "temperature": 0.7,
                "max_tokens": 280,
                "api_key": openai_api_key,
                "structured_outputs": False,
            }

            # Add base_url only if it's set
            openai_base_url = os.getenv("OPENAI_BASE_URL")
            if openai_base_url and openai_base_url.strip():
                model_params["base_url"] = openai_base_url

            self.model = OpenAIChat(**model_params)

        # Register only the tweet generation function
        self.register(self.generate_tweet)

    def generate_tweet(self, personality: str, topic: str = None) -> Tuple[bool, str]:
        """
        Generate a tweet using the model based on personality and topic, and post it.

        Args:
            personality (str): The personality/role to use for tweet generation
            topic (str, optional): Specific topic to tweet about
        Returns:
            tuple: (success: bool, message: str) - Success status and response message
        """
        try:
            # Generate prompt messages
            user_prompt = f"Generate a tweet as {personality}."
            if topic:
                user_prompt += f" The tweet should be about: {topic}."
            user_prompt += TWEET_REQUIREMENTS

            messages = [
                Message(role="system", content=SYSTEM_PROMPT),
                Message(role="user", content=user_prompt),
            ]

            # Generate tweet using the model
            response = self.model.invoke(messages=messages)
            # Extract content from the response
            if hasattr(response, "choices") and len(response.choices) > 0:
                tweet_content = response.choices[0].message.content.strip()
            else:
                tweet_content = str(response).strip()

            # Validate tweet length and hashtag presence
            if len(tweet_content) > 280:
                logger.warning(
                    f"Generated tweet exceeds 280 characters, length: {len(tweet_content)}"
                )
                tweet_content = tweet_content[:277] + "..."

            if "#" not in tweet_content:
                logger.warning(
                    "Generated tweet does not contain hashtags, regenerating..."
                )
                return self.generate_tweet(personality, topic)

            # Post the generated tweet
            logger.info(f"Posting generated tweet: {tweet_content}")
            return self.post_tweet(tweet_content)

        except Exception as error:
            logger.error(f"Error generating/posting tweet: {error}")
            return False, str(error)

    def post_tweet(self, tweet_content: str) -> Tuple[bool, str]:
        """
        Post a tweet using the Twitter handler.

        Args:
            tweet_content (str): The content to tweet
        Returns:
            tuple: (success: bool, message: str) - Success status and response message
        """
        try:
            success, response = self.twitter_handler.post_tweet(tweet_content)
            if success:
                return True, tweet_content
            return False, response
        except Exception as error:
            logger.error(f"Error posting tweet: {error}")
            return False, str(error)
