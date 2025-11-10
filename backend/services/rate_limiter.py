"""
Rate Limiter - Controls API usage to prevent abuse and manage costs

This service implements rate limiting with:
- Per-user request limits (hourly/daily)
- Token usage tracking
- In-memory storage (Phase 1 MVP)
- Sliding window algorithm
"""

import logging
import time
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a user tier"""
    requests_per_hour: int
    requests_per_day: int
    tokens_per_hour: int
    tokens_per_day: int


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Features:
    - Per-user request limits
    - Token usage tracking
    - Hourly and daily windows
    - Automatic cleanup of old data
    - Configurable tiers (Free, Pro, Enterprise)

    Note: This is Phase 1 MVP with in-memory storage.
    For production at scale, migrate to Redis for distributed rate limiting.
    """

    # Default rate limit tiers
    TIERS = {
        'free': RateLimitConfig(
            requests_per_hour=50,
            requests_per_day=200,
            tokens_per_hour=25000,
            tokens_per_day=100000
        ),
        'pro': RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=1000,
            tokens_per_hour=100000,
            tokens_per_day=500000
        ),
        'enterprise': RateLimitConfig(
            requests_per_hour=999999,
            requests_per_day=999999,
            tokens_per_hour=999999,
            tokens_per_day=999999
        )
    }

    def __init__(self):
        """Initialize rate limiter with in-memory storage"""
        # Request tracking: user_id -> list of (timestamp, tokens)
        self.request_log: Dict[str, list] = defaultdict(list)

        # User tier mapping: user_id -> tier_name
        self.user_tiers: Dict[str, str] = {}

        # Cleanup tracking
        self.last_cleanup = time.time()
        self.cleanup_interval = 3600  # 1 hour

        logger.info("Rate Limiter initialized (in-memory mode)")

    def _get_user_tier(self, user_id: str) -> str:
        """Get user's rate limit tier (default: free)"""
        return self.user_tiers.get(user_id, 'free')

    def _get_config(self, user_id: str) -> RateLimitConfig:
        """Get rate limit configuration for user"""
        tier = self._get_user_tier(user_id)
        return self.TIERS[tier]

    def _cleanup_old_entries(self, user_id: str):
        """Remove entries older than 24 hours"""
        if user_id not in self.request_log:
            return

        cutoff = time.time() - 86400  # 24 hours ago
        self.request_log[user_id] = [
            (ts, tokens) for ts, tokens in self.request_log[user_id]
            if ts > cutoff
        ]

        # Remove empty logs
        if not self.request_log[user_id]:
            del self.request_log[user_id]

    def _periodic_cleanup(self):
        """Periodically cleanup all old entries"""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            logger.info("Running periodic cleanup of rate limit data")
            cutoff = now - 86400

            for user_id in list(self.request_log.keys()):
                self.request_log[user_id] = [
                    (ts, tokens) for ts, tokens in self.request_log[user_id]
                    if ts > cutoff
                ]
                if not self.request_log[user_id]:
                    del self.request_log[user_id]

            self.last_cleanup = now
            logger.info(f"Cleanup complete. Active users: {len(self.request_log)}")

    def _count_in_window(
        self,
        user_id: str,
        window_seconds: int
    ) -> Tuple[int, int]:
        """
        Count requests and tokens in a time window.

        Args:
            user_id: User's Clerk ID
            window_seconds: Window size in seconds (3600 for hour, 86400 for day)

        Returns:
            (request_count, token_count)
        """
        if user_id not in self.request_log:
            return 0, 0

        cutoff = time.time() - window_seconds
        requests = 0
        tokens = 0

        for timestamp, token_count in self.request_log[user_id]:
            if timestamp > cutoff:
                requests += 1
                tokens += token_count

        return requests, tokens

    def check_rate_limit(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if user is within rate limits.

        Args:
            user_id: User's Clerk ID

        Returns:
            (allowed: bool, reason: str)
            - allowed: True if request should be allowed
            - reason: Explanation if blocked, "OK" if allowed
        """
        try:
            # Periodic cleanup
            self._periodic_cleanup()

            # Get user's rate limit config
            config = self._get_config(user_id)

            # Cleanup old entries for this user
            self._cleanup_old_entries(user_id)

            # Check hourly request limit
            hourly_requests, hourly_tokens = self._count_in_window(user_id, 3600)

            if hourly_requests >= config.requests_per_hour:
                tier = self._get_user_tier(user_id)
                logger.warning(
                    f"User {user_id[:8]}... hit hourly request limit: "
                    f"{hourly_requests}/{config.requests_per_hour} ({tier} tier)"
                )
                return False, (
                    f"Hourly request limit exceeded ({config.requests_per_hour} requests/hour). "
                    f"Please try again in a few minutes."
                )

            # Check hourly token limit
            if hourly_tokens >= config.tokens_per_hour:
                tier = self._get_user_tier(user_id)
                logger.warning(
                    f"User {user_id[:8]}... hit hourly token limit: "
                    f"{hourly_tokens}/{config.tokens_per_hour} ({tier} tier)"
                )
                return False, (
                    f"Hourly token limit exceeded ({config.tokens_per_hour} tokens/hour). "
                    f"Please try again in a few minutes."
                )

            # Check daily request limit
            daily_requests, daily_tokens = self._count_in_window(user_id, 86400)

            if daily_requests >= config.requests_per_day:
                tier = self._get_user_tier(user_id)
                logger.warning(
                    f"User {user_id[:8]}... hit daily request limit: "
                    f"{daily_requests}/{config.requests_per_day} ({tier} tier)"
                )
                return False, (
                    f"Daily request limit exceeded ({config.requests_per_day} requests/day). "
                    f"Please try again tomorrow or upgrade your plan."
                )

            # Check daily token limit
            if daily_tokens >= config.tokens_per_day:
                tier = self._get_user_tier(user_id)
                logger.warning(
                    f"User {user_id[:8]}... hit daily token limit: "
                    f"{daily_tokens}/{config.tokens_per_day} ({tier} tier)"
                )
                return False, (
                    f"Daily token limit exceeded ({config.tokens_per_day} tokens/day). "
                    f"Please try again tomorrow or upgrade your plan."
                )

            return True, "OK"

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}", exc_info=True)
            # Fail open (allow request) rather than blocking legitimate users
            return True, "OK"

    def track_request(self, user_id: str, tokens_used: int = 0):
        """
        Track a request for rate limiting.

        Args:
            user_id: User's Clerk ID
            tokens_used: Number of tokens used in the request
        """
        try:
            timestamp = time.time()
            self.request_log[user_id].append((timestamp, tokens_used))

            logger.debug(
                f"Tracked request: user={user_id[:8]}..., tokens={tokens_used}"
            )

        except Exception as e:
            logger.error(f"Error tracking request: {e}", exc_info=True)

    def get_user_usage(self, user_id: str) -> dict:
        """
        Get current usage statistics for a user.

        Args:
            user_id: User's Clerk ID

        Returns:
            Dictionary with usage stats
        """
        try:
            config = self._get_config(user_id)
            tier = self._get_user_tier(user_id)

            hourly_requests, hourly_tokens = self._count_in_window(user_id, 3600)
            daily_requests, daily_tokens = self._count_in_window(user_id, 86400)

            return {
                'tier': tier,
                'hourly': {
                    'requests': hourly_requests,
                    'requests_limit': config.requests_per_hour,
                    'requests_remaining': max(0, config.requests_per_hour - hourly_requests),
                    'tokens': hourly_tokens,
                    'tokens_limit': config.tokens_per_hour,
                    'tokens_remaining': max(0, config.tokens_per_hour - hourly_tokens)
                },
                'daily': {
                    'requests': daily_requests,
                    'requests_limit': config.requests_per_day,
                    'requests_remaining': max(0, config.requests_per_day - daily_requests),
                    'tokens': daily_tokens,
                    'tokens_limit': config.tokens_per_day,
                    'tokens_remaining': max(0, config.tokens_per_day - daily_tokens)
                }
            }

        except Exception as e:
            logger.error(f"Error getting user usage: {e}", exc_info=True)
            return {}

    def set_user_tier(self, user_id: str, tier: str):
        """
        Set user's rate limit tier.

        Args:
            user_id: User's Clerk ID
            tier: Tier name ('free', 'pro', 'enterprise')
        """
        if tier not in self.TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {list(self.TIERS.keys())}")

        self.user_tiers[user_id] = tier
        logger.info(f"Set user {user_id[:8]}... to {tier} tier")

    def get_stats(self) -> dict:
        """Get global rate limiter statistics"""
        total_users = len(self.request_log)
        tier_counts = defaultdict(int)

        for user_id in self.request_log.keys():
            tier = self._get_user_tier(user_id)
            tier_counts[tier] += 1

        return {
            'active_users': total_users,
            'users_by_tier': dict(tier_counts),
            'last_cleanup': datetime.fromtimestamp(self.last_cleanup).isoformat()
        }


# Global singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
