"""Redis client configuration and utilities."""

import json
import redis
from typing import Any, Optional, Dict, List
from datetime import timedelta

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis client wrapper with utility methods."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
    def ping(self) -> bool:
        """Check Redis connection health."""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Store JSON data in Redis with optional expiration."""
        try:
            json_value = json.dumps(value, default=str)
            return self.redis_client.set(key, json_value, ex=ex)
        except Exception as e:
            logger.error(f"Failed to set JSON key {key}: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and deserialize JSON data from Redis."""
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error(f"Failed to get JSON key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check key existence {key}: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key."""
        try:
            return bool(self.redis_client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern."""
        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
            return []
    
    def flushdb(self) -> bool:
        """Clear all keys from current database (use with caution!)."""
        try:
            return self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Failed to flush database: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()


def get_cache_key(prefix: str, *args: str) -> str:
    """Generate a standardized cache key."""
    parts = [prefix] + list(args)
    return ":".join(str(part) for part in parts)


def cache_analysis_result(
    task_id: str, 
    file_path: str, 
    analysis_type: str, 
    result: Dict[str, Any],
    ttl_hours: int = 24
) -> bool:
    """Cache analysis result for a specific file and analysis type."""
    cache_key = get_cache_key("analysis", task_id, file_path, analysis_type)
    ttl_seconds = ttl_hours * 3600
    return redis_client.set_json(cache_key, result, ex=ttl_seconds)


def get_cached_analysis_result(
    task_id: str, 
    file_path: str, 
    analysis_type: str
) -> Optional[Dict[str, Any]]:
    """Retrieve cached analysis result."""
    cache_key = get_cache_key("analysis", task_id, file_path, analysis_type)
    return redis_client.get_json(cache_key)


def cache_task_progress(task_id: str, progress_data: Dict[str, Any]) -> bool:
    """Cache task progress data."""
    cache_key = get_cache_key("progress", task_id)
    # Progress data expires in 1 hour
    return redis_client.set_json(cache_key, progress_data, ex=3600)


def get_cached_task_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached task progress data."""
    cache_key = get_cache_key("progress", task_id)
    return redis_client.get_json(cache_key)