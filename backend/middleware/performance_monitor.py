"""
Performance Monitoring Middleware for Flask

Tracks all API requests and logs metrics to:
- api_usage table in Supabase (persistent storage)
- Application logs (real-time monitoring)
- In-memory stats (quick access)

Features:
- Automatic request/response time tracking
- Success/error rate monitoring
- Token usage tracking (for LLM endpoints)
- User-specific metrics
- Endpoint performance analytics

Usage:
    from middleware.performance_monitor import setup_performance_monitoring

    app = Flask(__name__)
    setup_performance_monitoring(app)
"""

import time
import logging
from flask import g, request, Flask
from datetime import datetime
from typing import Optional
import traceback

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Centralized performance monitoring for Flask applications.

    Tracks:
    - Request/response times
    - Success/error rates
    - Token usage (for LLM endpoints)
    - Per-endpoint metrics
    - Per-user metrics
    """

    def __init__(self, supabase_client=None):
        """
        Initialize performance monitor.

        Args:
            supabase_client: Optional Supabase client for database logging
        """
        self.supabase = supabase_client
        self.stats = {
            'total_requests': 0,
            'total_errors': 0,
            'total_response_time': 0,
            'endpoints': {},  # Endpoint-specific stats
        }
        self.enabled = True

    def before_request(self):
        """Called before each request. Starts timing."""
        g.start_time = time.perf_counter()
        g.request_id = f"{int(time.time() * 1000)}-{id(request)}"

    def after_request(self, response):
        """Called after each request. Logs metrics."""
        if not self.enabled or not hasattr(g, 'start_time'):
            return response

        try:
            # Calculate response time
            response_time_ms = (time.perf_counter() - g.start_time) * 1000

            # Extract request info
            endpoint = request.endpoint or 'unknown'
            method = request.method
            path = request.path
            status_code = response.status_code
            success = 200 <= status_code < 400

            # Get user ID from g (set by auth middleware)
            user_id = getattr(g, 'user_id', None)

            # Get tokens used (set by LLM endpoints)
            tokens_used = getattr(g, 'tokens_used', None)

            # Get model used (set by LLM endpoints)
            model = getattr(g, 'model_used', None)

            # Get conversation ID (set by chat endpoints)
            conversation_id = getattr(g, 'conversation_id', None)

            # Update in-memory stats
            self._update_stats(endpoint, response_time_ms, success)

            # Log to console (structured logging)
            log_data = {
                'request_id': g.request_id,
                'method': method,
                'path': path,
                'endpoint': endpoint,
                'status': status_code,
                'response_time_ms': f'{response_time_ms:.2f}',
                'success': success,
            }
            if user_id:
                log_data['user_id'] = user_id[:8] + '...'
            if tokens_used:
                log_data['tokens'] = tokens_used
            if model:
                log_data['model'] = model

            logger.info(f"API Request: {log_data}")

            # Save to database in background thread (non-blocking)
            # NOTE: Disabled synchronous DB logging - it was adding 3+ seconds to every request!
            # To re-enable, use a proper async queue like Celery or Redis.
            # if self.supabase and path.startswith('/api/'):
            #     self._save_to_database(
            #         endpoint=path,
            #         method=method,
            #         response_time_ms=response_time_ms,
            #         success=success,
            #         status_code=status_code,
            #         user_id=user_id,
            #         tokens_used=tokens_used,
            #         model=model,
            #         conversation_id=conversation_id,
            #         error_message=getattr(g, 'error_message', None)
            #     )

            # Add response time header for frontend
            response.headers['X-Response-Time'] = f'{response_time_ms:.2f}ms'

        except Exception as e:
            logger.error(f"Error in performance monitoring: {e}", exc_info=True)

        return response

    def _update_stats(self, endpoint: str, response_time_ms: float, success: bool):
        """Update in-memory statistics."""
        self.stats['total_requests'] += 1
        self.stats['total_response_time'] += response_time_ms

        if not success:
            self.stats['total_errors'] += 1

        # Per-endpoint stats
        if endpoint not in self.stats['endpoints']:
            self.stats['endpoints'][endpoint] = {
                'count': 0,
                'errors': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }

        ep_stats = self.stats['endpoints'][endpoint]
        ep_stats['count'] += 1
        ep_stats['total_time'] += response_time_ms
        ep_stats['min_time'] = min(ep_stats['min_time'], response_time_ms)
        ep_stats['max_time'] = max(ep_stats['max_time'], response_time_ms)

        if not success:
            ep_stats['errors'] += 1

    def _save_to_database(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        success: bool,
        status_code: int,
        user_id: Optional[str] = None,
        tokens_used: Optional[int] = None,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Save request metrics to api_usage table.

        This runs in the same thread but is designed to be fast.
        If Supabase is slow, consider using a background queue.
        """
        try:
            data = {
                'timestamp': datetime.utcnow().isoformat(),
                'endpoint': endpoint,
                'method': method,
                'response_time_ms': round(response_time_ms, 2),
                'success': success,
                'status_code': status_code,
            }

            # Add optional fields if present
            if user_id:
                data['user_id'] = user_id
            if tokens_used:
                data['tokens_used'] = tokens_used
            if model:
                data['model'] = model
            if conversation_id:
                data['conversation_id'] = conversation_id
            if error_message:
                data['error_message'] = error_message[:500]  # Limit length

            # Insert into Supabase
            self.supabase.table('api_usage').insert(data).execute()

        except Exception as e:
            # Don't let database errors break the request
            logger.warning(f"Failed to save metrics to database: {e}")

    def get_stats(self):
        """Get current in-memory statistics."""
        stats = self.stats.copy()

        # Calculate averages
        if stats['total_requests'] > 0:
            stats['avg_response_time'] = stats['total_response_time'] / stats['total_requests']
            stats['error_rate'] = stats['total_errors'] / stats['total_requests']
        else:
            stats['avg_response_time'] = 0
            stats['error_rate'] = 0

        # Calculate per-endpoint averages
        for endpoint, ep_stats in stats['endpoints'].items():
            if ep_stats['count'] > 0:
                ep_stats['avg_time'] = ep_stats['total_time'] / ep_stats['count']
                ep_stats['error_rate'] = ep_stats['errors'] / ep_stats['count']
            else:
                ep_stats['avg_time'] = 0
                ep_stats['error_rate'] = 0

        return stats

    def get_database_stats(self, time_range: str = '1h'):
        """
        Get statistics from database for a given time range.

        Args:
            time_range: '1h', '24h', '7d', or '30d'

        Returns:
            dict: Statistics from database
        """
        if not self.supabase:
            return {'error': 'Database not configured'}

        try:
            # Calculate timestamp for time range
            from datetime import timedelta
            now = datetime.utcnow()

            time_deltas = {
                '1h': timedelta(hours=1),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }

            delta = time_deltas.get(time_range, timedelta(hours=1))
            start_time = (now - delta).isoformat()

            # Query api_usage table
            result = self.supabase.table('api_usage')\
                .select('*')\
                .gte('timestamp', start_time)\
                .execute()

            if not result.data:
                return {
                    'time_range': time_range,
                    'total_requests': 0,
                    'avg_response_time': 0,
                    'error_rate': 0,
                    'endpoints': {}
                }

            # Calculate statistics
            records = result.data
            total_requests = len(records)
            total_errors = sum(1 for r in records if not r['success'])
            total_response_time = sum(r['response_time_ms'] for r in records)

            # Per-endpoint stats
            endpoints = {}
            for record in records:
                ep = record['endpoint']
                if ep not in endpoints:
                    endpoints[ep] = {
                        'count': 0,
                        'errors': 0,
                        'total_time': 0,
                        'min_time': float('inf'),
                        'max_time': 0
                    }

                endpoints[ep]['count'] += 1
                endpoints[ep]['total_time'] += record['response_time_ms']
                endpoints[ep]['min_time'] = min(endpoints[ep]['min_time'], record['response_time_ms'])
                endpoints[ep]['max_time'] = max(endpoints[ep]['max_time'], record['response_time_ms'])

                if not record['success']:
                    endpoints[ep]['errors'] += 1

            # Calculate averages
            for ep_stats in endpoints.values():
                if ep_stats['count'] > 0:
                    ep_stats['avg_time'] = ep_stats['total_time'] / ep_stats['count']
                    ep_stats['error_rate'] = ep_stats['errors'] / ep_stats['count']

            return {
                'time_range': time_range,
                'total_requests': total_requests,
                'total_errors': total_errors,
                'avg_response_time': total_response_time / total_requests if total_requests > 0 else 0,
                'error_rate': total_errors / total_requests if total_requests > 0 else 0,
                'endpoints': endpoints
            }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}", exc_info=True)
            return {'error': str(e)}


# Global instance
_monitor: Optional[PerformanceMonitor] = None


def setup_performance_monitoring(app: Flask, supabase_client=None) -> PerformanceMonitor:
    """
    Set up performance monitoring for a Flask application.

    Args:
        app: Flask application instance
        supabase_client: Optional Supabase client for database logging

    Returns:
        PerformanceMonitor instance

    Example:
        from middleware.performance_monitor import setup_performance_monitoring

        app = Flask(__name__)
        monitor = setup_performance_monitoring(app, supabase)
    """
    global _monitor

    _monitor = PerformanceMonitor(supabase_client)

    # Register Flask hooks
    app.before_request(_monitor.before_request)
    app.after_request(_monitor.after_request)

    logger.info("✅ Performance monitoring enabled")

    return _monitor


def get_monitor() -> Optional[PerformanceMonitor]:
    """Get the global performance monitor instance."""
    return _monitor
