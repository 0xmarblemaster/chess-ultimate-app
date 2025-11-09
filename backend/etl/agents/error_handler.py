import logging
import time
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
import traceback
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorType(Enum):
    WEAVIATE_CONNECTION = "weaviate_connection"
    STOCKFISH_ENGINE = "stockfish_engine"
    LLM_API = "llm_api"
    AGENT_FAILURE = "agent_failure"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

class RAGErrorHandler:
    """Centralized error handling for RAG pipeline with graceful fallbacks"""
    
    def __init__(self):
        self.error_counts = {}
        self.recent_errors = []
        self.fallback_strategies = {}
        self.max_recent_errors = 100
        
        # Register default fallback strategies
        self._register_default_fallbacks()
    
    def _register_default_fallbacks(self):
        """Register default fallback strategies for common error types"""
        
        self.fallback_strategies[ErrorType.WEAVIATE_CONNECTION] = {
            'strategy': 'use_simplified_pipeline',
            'message': 'Database unavailable, using simplified response mode'
        }
        
        self.fallback_strategies[ErrorType.STOCKFISH_ENGINE] = {
            'strategy': 'skip_analysis',
            'message': 'Engine analysis unavailable, providing text-only response'
        }
        
        self.fallback_strategies[ErrorType.LLM_API] = {
            'strategy': 'use_template_response',
            'message': 'AI service temporarily unavailable'
        }
        
        self.fallback_strategies[ErrorType.AGENT_FAILURE] = {
            'strategy': 'use_direct_response',
            'message': 'Using simplified response mode'
        }
    
    def handle_error(self, 
                    error: Exception, 
                    error_type: ErrorType, 
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle an error with appropriate logging and fallback strategy
        
        Args:
            error: The exception that occurred
            error_type: Type of error for routing to appropriate handler
            severity: Severity level of the error
            context: Additional context about where the error occurred
            
        Returns:
            Dict containing fallback response and metadata
        """
        error_info = {
            'timestamp': time.time(),
            'error_type': error_type.value,
            'severity': severity.value,
            'message': str(error),
            'context': context or {},
            'traceback': traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
        
        # Track error frequency
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.recent_errors.append(error_info)
        
        # Keep only recent errors to prevent memory issues
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[-self.max_recent_errors:]
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR [{error_type.value}]: {error}", exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY [{error_type.value}]: {error}", exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY [{error_type.value}]: {error}")
        else:
            logger.info(f"LOW SEVERITY [{error_type.value}]: {error}")
        
        # Get fallback strategy
        fallback = self._get_fallback_strategy(error_type, context)
        
        return {
            'error_handled': True,
            'fallback_strategy': fallback['strategy'],
            'user_message': fallback['message'],
            'error_info': error_info,
            'should_retry': severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]
        }
    
    def _get_fallback_strategy(self, error_type: ErrorType, context: Optional[Dict] = None) -> Dict[str, str]:
        """Get appropriate fallback strategy for error type"""
        return self.fallback_strategies.get(error_type, {
            'strategy': 'use_generic_fallback',
            'message': 'Service temporarily unavailable, please try again'
        })
    
    def circuit_breaker(self, error_threshold: int = 5, time_window: int = 300):
        """
        Decorator that implements circuit breaker pattern for agent functions
        
        Args:
            error_threshold: Number of errors before opening circuit
            time_window: Time window in seconds for error counting
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Check if circuit should be open
                if self._should_circuit_break(func.__name__, error_threshold, time_window):
                    raise Exception(f"Circuit breaker open for {func.__name__}")
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Record the failure
                    self._record_circuit_failure(func.__name__)
                    raise
                    
            return wrapper
        return decorator
    
    def _should_circuit_break(self, function_name: str, threshold: int, window: int) -> bool:
        """Check if circuit breaker should activate for a function"""
        current_time = time.time()
        recent_failures = [
            error for error in self.recent_errors 
            if (current_time - error['timestamp']) < window 
            and error['context'].get('function') == function_name
        ]
        return len(recent_failures) >= threshold
    
    def _record_circuit_failure(self, function_name: str):
        """Record a failure for circuit breaker tracking"""
        self.recent_errors.append({
            'timestamp': time.time(),
            'error_type': 'circuit_breaker_failure',
            'context': {'function': function_name}
        })
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        current_time = time.time()
        recent_errors_1h = [
            error for error in self.recent_errors 
            if (current_time - error['timestamp']) < 3600
        ]
        
        return {
            'total_errors': len(self.recent_errors),
            'errors_last_hour': len(recent_errors_1h),
            'error_types': dict(self.error_counts),
            'most_recent_error': self.recent_errors[-1] if self.recent_errors else None,
            'error_rate_per_hour': len(recent_errors_1h)
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health based on error patterns"""
        stats = self.get_error_stats()
        
        # Simple health scoring
        errors_last_hour = stats['errors_last_hour']
        if errors_last_hour == 0:
            health = "excellent"
        elif errors_last_hour < 5:
            health = "good"
        elif errors_last_hour < 15:
            health = "fair"
        else:
            health = "poor"
        
        return {
            'health': health,
            'errors_last_hour': errors_last_hour,
            'critical_errors': sum(1 for e in self.recent_errors[-20:] if e.get('severity') == 'critical'),
            'recommendations': self._get_health_recommendations(stats)
        }
    
    def _get_health_recommendations(self, stats: Dict) -> List[str]:
        """Get recommendations based on error patterns"""
        recommendations = []
        
        if stats['errors_last_hour'] > 10:
            recommendations.append("High error rate detected. Consider investigating system health.")
        
        error_types = stats['error_types']
        if error_types.get(ErrorType.WEAVIATE_CONNECTION, 0) > 3:
            recommendations.append("Frequent database connection issues. Check Weaviate service.")
        
        if error_types.get(ErrorType.STOCKFISH_ENGINE, 0) > 3:
            recommendations.append("Stockfish engine issues detected. Check engine installation.")
        
        if error_types.get(ErrorType.LLM_API, 0) > 3:
            recommendations.append("LLM API issues detected. Check API keys and rate limits.")
        
        return recommendations

def safe_execute(func: Callable, 
                error_handler: RAGErrorHandler,
                error_type: ErrorType = ErrorType.UNKNOWN,
                default_return: Any = None,
                context: Optional[Dict] = None) -> Any:
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        error_handler: Error handler instance
        error_type: Type of error expected
        default_return: Default value to return on error
        context: Additional context for error handling
        
    Returns:
        Function result or default_return on error
    """
    try:
        return func()
    except Exception as e:
        error_result = error_handler.handle_error(e, error_type, context=context)
        logger.warning(f"Safe execution failed: {error_result['user_message']}")
        return default_return

# Global error handler instance
rag_error_handler = RAGErrorHandler() 