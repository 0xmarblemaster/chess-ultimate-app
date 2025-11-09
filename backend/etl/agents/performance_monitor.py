import time
import logging
from functools import wraps
from typing import Dict, Any, Optional
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Thread-safe performance monitoring for RAG pipeline"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()
        self.session_metrics = {}
    
    def timer(self, operation_name: str):
        """Decorator to time operations"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration = time.time() - start_time
                    self.record_metric(operation_name, duration, success, error)
                return result
            return wrapper
        return decorator
    
    def record_metric(self, operation: str, duration: float, success: bool, error: Optional[str] = None):
        """Record a performance metric"""
        with self.lock:
            if operation not in self.metrics:
                self.metrics[operation] = {
                    'total_calls': 0,
                    'total_duration': 0.0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'avg_duration': 0.0,
                    'last_error': None,
                    'last_call': None
                }
            
            metric = self.metrics[operation]
            metric['total_calls'] += 1
            metric['total_duration'] += duration
            metric['last_call'] = datetime.now().isoformat()
            
            if success:
                metric['successful_calls'] += 1
            else:
                metric['failed_calls'] += 1
                metric['last_error'] = error
            
            metric['avg_duration'] = metric['total_duration'] / metric['total_calls']
            
            logger.info(f"Performance: {operation} took {duration:.3f}s (success: {success})")
    
    def start_session_tracking(self, session_id: str):
        """Start tracking metrics for a specific session"""
        with self.lock:
            self.session_metrics[session_id] = {
                'start_time': time.time(),
                'operations': [],
                'total_duration': 0.0
            }
    
    def record_session_operation(self, session_id: str, operation: str, duration: float):
        """Record an operation for a specific session"""
        with self.lock:
            if session_id in self.session_metrics:
                self.session_metrics[session_id]['operations'].append({
                    'operation': operation,
                    'duration': duration,
                    'timestamp': time.time()
                })
                self.session_metrics[session_id]['total_duration'] += duration
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics"""
        with self.lock:
            return self.metrics.copy()
    
    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get metrics for a specific session"""
        with self.lock:
            return self.session_metrics.get(session_id, {})
    
    def log_performance_summary(self):
        """Log a summary of all performance metrics"""
        with self.lock:
            logger.info("=== RAG Performance Summary ===")
            for operation, metrics in self.metrics.items():
                success_rate = (metrics['successful_calls'] / metrics['total_calls']) * 100 if metrics['total_calls'] > 0 else 0
                logger.info(f"{operation}: {metrics['total_calls']} calls, {metrics['avg_duration']:.3f}s avg, {success_rate:.1f}% success")

# Global performance monitor instance
performance_monitor = PerformanceMonitor() 