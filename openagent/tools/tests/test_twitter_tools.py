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
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
        ]

    def test_environment_variables(self):
        """Test if all required environment variables are present"""
        print("\ntest_environment_variables")
        missing_vars = [var for var in self.required_env_vars if not os.getenv(var)]

        if missing_vars:
            self.fail(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def test_tweet_generation_and_posting(self):
        """Test tweet generation with personality and posting"""
        print("\ntest_tweet_generation_and_posting")

        # Test case for tweet generation and posting
        personality = "tech enthusiast"
        description = "AI and machine learning innovations"
        expected_terms = ["AI", "tech", "machine learning", "innovation"]

        try:
            # Generate and post tweet
            print(
                f"\nGenerating and posting tweet as {personality} about {description}..."
            )
            success, tweet_content = self.tweet_tools.generate_tweet(
                personality=personality, description=description
            )

            # Validate the result
            self.assertTrue(
                success, f"Tweet generation/posting failed: {tweet_content}"
            )
            print("✓ Tweet generated and posted successfully")
            print(f"Tweet content: {tweet_content}")

            # Validate tweet content
            self.assertTrue(
                "#" in tweet_content, "Tweet should contain at least one hashtag"
            )
            found_terms = [
                term for term in expected_terms if term.lower() in tweet_content.lower()
            ]
            self.assertTrue(
                len(found_terms) > 0,
                f"Tweet should contain at least one of {expected_terms}. Content: {tweet_content}",
            )

            print("✓ Tweet content validation passed")
            print(f"Found terms: {', '.join(found_terms)}")

        except Exception as e:
            self.fail(f"Tweet generation and posting failed: {e!s}")


if __name__ == "__main__":
    print("\n=== Running Twitter Tools Tests ===\n")
    unittest.main()
