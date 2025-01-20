import os
import unittest
from dotenv import load_dotenv
from ..twitter.tweet_generator import TweetGeneratorTools

load_dotenv()


class TestTwitterTools(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tweet_tools = TweetGeneratorTools()
        self.required_env_vars = [
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
        ]

    def test_environment_variables(self):
        """Test if all required environment variables are present"""
        print("\ntest_environment_variables")
        missing_vars = []
        for var in self.required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.fail(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def test_tweet_generation_and_posting(self):
        """Test tweet generation with personality and posting"""
        print("\ntest_tweet_generation_and_posting")

        # Test case for tweet generation
        personality = "tech enthusiast"
        topic = "AI and machine learning innovations"
        expected_terms = ["AI", "tech", "machine learning", "innovation"]

        try:
            # Generate tweet
            print(f"\nGenerating tweet as {personality} about {topic}...")
            tweet_content = self.tweet_tools.generate_tweet(
                personality=personality, topic=topic
            )

            # Validate generated tweet
            self.assertIsInstance(tweet_content, str, "Tweet should be a string")
            self.assertTrue(
                0 < len(tweet_content) <= 280,
                f"Tweet length ({len(tweet_content)}) should be between 1 and 280 characters",
            )
            self.assertTrue(
                "#" in tweet_content, "Tweet should contain at least one hashtag"
            )

            # Content validation
            found_terms = [
                term for term in expected_terms if term.lower() in tweet_content.lower()
            ]
            self.assertTrue(
                len(found_terms) > 0,
                f"Tweet should contain at least one of {expected_terms}. Content: {tweet_content}",
            )

            print(f"✓ Generated tweet ({len(tweet_content)} chars):")
            print("-" * 60)
            print(tweet_content)
            print("-" * 60)
            print(f"Found terms: {', '.join(found_terms)}")

            # Post the generated tweet
            print("\nPosting generated tweet...")
            success, message = self.tweet_tools.post_tweet(tweet_content)
            self.assertTrue(success, f"Tweet posting failed: {message}")
            print(f"✓ Tweet posted successfully: {message}")

        except Exception as e:
            self.fail(f"Tweet generation and posting failed: {str(e)}")


if __name__ == "__main__":
    print("\n=== Running Twitter Tools Tests ===\n")
    unittest.main()
