# ReviewCheckk Bot - Caching System
import time
import logging
from typing import Dict, Optional, Any
from config import CACHE_TTL, MAX_CACHE_SIZE

logger = logging.getLogger(__name__)

class ProductCache:
    """Simple in-memory cache for product data."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached product data."""
        try:
            if key not in self._cache:
                return None
            
            # Check if expired
            if time.time() - self._timestamps[key] > CACHE_TTL:
                self._remove(key)
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return self._cache[key]
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Set cached product data."""
        try:
            # Clean old entries if cache is full
            if len(self._cache) >= MAX_CACHE_SIZE:
                self._cleanup()
            
            self._cache[key] = value
            self._timestamps[key] = time.time()
            logger.debug(f"Cache set for key: {key}")
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
    
    def _remove(self, key: str) -> None:
        """Remove item from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def _cleanup(self) -> None:
        """Remove expired entries and oldest entries if needed."""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, timestamp in self._timestamps.items()
            if current_time - timestamp > CACHE_TTL
        ]
        
        for key in expired_keys:
            self._remove(key)
        
        # If still over limit, remove oldest entries
        if len(self._cache) >= MAX_CACHE_SIZE:
            # Sort by timestamp and remove oldest
            sorted_items = sorted(self._timestamps.items(), key=lambda x: x[1])
            items_to_remove = len(self._cache) - MAX_CACHE_SIZE + 10  # Remove extra for buffer
            
            for key, _ in sorted_items[:items_to_remove]:
                self._remove(key)
        
        logger.info(f"Cache cleanup completed. Current size: {len(self._cache)}")
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("Cache cleared")
