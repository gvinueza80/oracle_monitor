"""Redis caching utilities"""

import json
import logging
from typing import Any, Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis caching wrapper"""

    def __init__(self, url: str):
        """Initialize Redis connection"""
        try:
            self.client = redis.from_url(url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.client is not None

    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache"""
        if not self.is_connected():
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def get_json(self, key: str) -> Optional[dict]:
        """Get a JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for key {key}")
                return None
        return None

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set a value in cache"""
        if not self.is_connected():
            return False
        try:
            self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def set_json(self, key: str, value: dict, ttl: int = 300) -> bool:
        """Set a JSON value in cache"""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Failed to serialize JSON for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self.is_connected():
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.is_connected():
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis pattern DELETE error for pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists"""
        if not self.is_connected():
            return False
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a value"""
        if not self.is_connected():
            return None
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key"""
        if not self.is_connected():
            return False
        try:
            return self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    def close(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")


# Global cache instance
redis_cache = RedisCache(settings.REDIS_URL)


# Cache key patterns
def instance_metrics_key(instance_id: str, metric_type: str) -> str:
    """Generate cache key for instance metrics"""
    return f"metrics:{instance_id}:{metric_type}"


def instance_sessions_key(instance_id: str) -> str:
    """Generate cache key for instance sessions"""
    return f"sessions:{instance_id}"


def instance_locks_key(instance_id: str) -> str:
    """Generate cache key for instance locks"""
    return f"locks:{instance_id}"


def user_permissions_key(user_id: str) -> str:
    """Generate cache key for user permissions"""
    return f"user_perms:{user_id}"


def instance_health_key(instance_id: str) -> str:
    """Generate cache key for instance health status"""
    return f"instance_health:{instance_id}"
