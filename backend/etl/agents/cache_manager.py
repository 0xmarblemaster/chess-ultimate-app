import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
import threading

logger = logging.getLogger(__name__)

class CacheManager:
    """Thread-safe in-memory cache for expensive operations like Stockfish analysis"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):  # 5 minute TTL
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, fen: str, **kwargs) -> str:
        """Generate a cache key for given FEN and parameters"""
        # Create a string that includes FEN and any additional parameters
        key_data = f"{fen}_{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired"""
        return time.time() - timestamp > self.ttl_seconds
    
    def _evict_oldest(self):
        """Remove oldest entry when cache is full"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
        logger.debug(f"Cache: Evicted oldest entry {oldest_key}")
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (data, timestamp) in self.cache.items() 
            if self._is_expired(timestamp)
        ]
        
        for key in expired_keys:
            del self.cache[key]
            del self.access_times[key]
        
        if expired_keys:
            logger.debug(f"Cache: Cleaned up {len(expired_keys)} expired entries")
    
    def get(self, fen: str, **kwargs) -> Optional[Any]:
        """Get cached result for FEN analysis"""
        key = self._generate_key(fen, **kwargs)
        
        with self.lock:
            if key in self.cache:
                data, timestamp = self.cache[key]
                if not self._is_expired(timestamp):
                    self.access_times[key] = time.time()  # Update access time
                    logger.debug(f"Cache HIT for FEN: {fen[:20]}...")
                    return data
                else:
                    # Remove expired entry
                    del self.cache[key]
                    del self.access_times[key]
                    logger.debug(f"Cache EXPIRED for FEN: {fen[:20]}...")
        
        logger.debug(f"Cache MISS for FEN: {fen[:20]}...")
        return None
    
    def set(self, fen: str, result: Any, **kwargs) -> None:
        """Cache result for FEN analysis"""
        key = self._generate_key(fen, **kwargs)
        current_time = time.time()
        
        with self.lock:
            # Clean up expired entries periodically
            if len(self.cache) % 10 == 0:  # Clean every 10 operations
                self._cleanup_expired()
            
            # Evict oldest if cache is full
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
            
            self.cache[key] = (result, current_time)
            self.access_times[key] = current_time
            logger.debug(f"Cache SET for FEN: {fen[:20]}... (cache size: {len(self.cache)})")
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'utilization': len(self.cache) / self.max_size if self.max_size > 0 else 0
            }

# Global cache instances
stockfish_cache = CacheManager(max_size=50, ttl_seconds=600)  # 10 minute TTL for Stockfish
query_cache = CacheManager(max_size=100, ttl_seconds=300)     # 5 minute TTL for queries 