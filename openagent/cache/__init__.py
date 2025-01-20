from redis import Redis
import os
from typing import Optional


class RedisManager:
    _instance = None
    _client: Optional[Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init(cls) -> None:
        """Initialize the Redis connection."""
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            redis_url = (
                f"redis://{os.getenv('REDIS_HOST', 'localhost')}:"
                f"{os.getenv('REDIS_PORT', 6379)}/"
                f"{os.getenv('REDIS_DB', 0)}"
            )

        cls._client = Redis.from_url(redis_url, decode_responses=True)

    @classmethod
    def get_client(cls) -> Redis:
        """Get the Redis client."""
        if cls._client is None:
            raise RuntimeError("Redis not initialized. Call init() first.")
        return cls._client


__all__ = ["RedisManager"]
