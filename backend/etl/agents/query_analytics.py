import time
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QueryAnalytics:
    """Analytics tracking for RAG queries to understand user behavior and optimize routing"""
    
    def __init__(self):
        self.query_history = []
        self.session_data = defaultdict(list)
        self.classification_accuracy = defaultdict(int)
        self.query_patterns = Counter()
        self.response_times = defaultdict(list)
        self.error_patterns = Counter()
        self.lock = threading.Lock()
        
    def track_query(self, 
                   session_id: str,
                   query: str, 
                   classification: str, 
                   success: bool,
                   response_time: float,
                   error_message: Optional[str] = None,
                   retrieved_count: int = 0,
                   current_fen: Optional[str] = None):
        """Track a query with its metadata and results"""
        
        with self.lock:
            query_data = {
                'timestamp': time.time(),
                'session_id': session_id,
                'query': query,
                'query_length': len(query.split()),
                'classification': classification,
                'success': success,
                'response_time': response_time,
                'error_message': error_message,
                'retrieved_count': retrieved_count,
                'current_fen': current_fen,
                'hour': datetime.now().hour
            }
            
            # Add to query history
            self.query_history.append(query_data)
            
            # Track per session
            self.session_data[session_id].append(query_data)
            
            # Track classification accuracy
            self.classification_accuracy[classification] += 1 if success else 0
            
            # Extract and track query patterns
            self._extract_patterns(query, classification)
            
            # Track response times by classification
            self.response_times[classification].append(response_time)
            
            # Track error patterns
            if not success and error_message:
                self.error_patterns[classification] += 1
                
            # Keep only last 1000 queries to prevent memory issues
            if len(self.query_history) > 1000:
                self.query_history = self.query_history[-1000:]
                
            logger.debug(f"Tracked query: {query[:50]}... -> {classification} (success: {success}, {response_time:.2f}s)")
    
    def _extract_patterns(self, query: str, classification: str):
        """Extract patterns from queries for analysis"""
        query_lower = query.lower()
        
        # Common query patterns
        patterns = []
        
        # Question words
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which']
        for word in question_words:
            if query_lower.startswith(word):
                patterns.append(f"starts_with_{word}")
        
        # Chess terms
        chess_terms = ['fen', 'opening', 'game', 'move', 'position', 'analysis']
        for term in chess_terms:
            if term in query_lower:
                patterns.append(f"contains_{term}")
        
        # Player names (simple heuristic)
        if any(word.istitle() and len(word) > 3 for word in query.split()):
            patterns.append("contains_proper_name")
        
        # Store patterns with classification
        for pattern in patterns:
            self.query_patterns[f"{classification}:{pattern}"] += 1
    
    def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get analytics for a specific session"""
        with self.lock:
            session_queries = self.session_data.get(session_id, [])
            
            if not session_queries:
                return {"session_id": session_id, "query_count": 0}
            
            total_queries = len(session_queries)
            successful_queries = sum(1 for q in session_queries if q['success'])
            avg_response_time = sum(q['response_time'] for q in session_queries) / total_queries
            
            classifications = Counter(q['classification'] for q in session_queries)
            
            return {
                "session_id": session_id,
                "query_count": total_queries,
                "success_rate": successful_queries / total_queries if total_queries > 0 else 0,
                "avg_response_time": avg_response_time,
                "classifications": dict(classifications),
                "session_duration": session_queries[-1]['timestamp'] - session_queries[0]['timestamp'],
                "last_query_time": session_queries[-1]['timestamp']
            }
    
    def get_global_analytics(self) -> Dict[str, Any]:
        """Get overall analytics across all sessions"""
        with self.lock:
            if not self.query_history:
                return {"message": "No queries tracked yet"}
            
            total_queries = len(self.query_history)
            successful_queries = sum(1 for q in self.query_history if q['success'])
            
            # Classification breakdown
            classifications = Counter(q['classification'] for q in self.query_history)
            
            # Response time statistics
            all_response_times = [q['response_time'] for q in self.query_history]
            avg_response_time = sum(all_response_times) / len(all_response_times)
            
            # Peak hours
            hour_distribution = Counter(q['hour'] for q in self.query_history)
            peak_hour = hour_distribution.most_common(1)[0] if hour_distribution else (0, 0)
            
            # Most common patterns
            top_patterns = self.query_patterns.most_common(10)
            
            # Recent performance (last 50 queries)
            recent_queries = self.query_history[-50:]
            recent_success_rate = sum(1 for q in recent_queries if q['success']) / len(recent_queries) if recent_queries else 0
            
            return {
                "total_queries": total_queries,
                "success_rate": successful_queries / total_queries if total_queries > 0 else 0,
                "recent_success_rate": recent_success_rate,
                "avg_response_time": avg_response_time,
                "classifications": dict(classifications),
                "peak_hour": peak_hour[0],
                "peak_hour_count": peak_hour[1],
                "top_patterns": top_patterns,
                "unique_sessions": len(self.session_data),
                "error_rate_by_classification": {
                    classification: self.error_patterns[classification] / count
                    for classification, count in classifications.items()
                    if count > 0
                }
            }
    
    def get_classification_performance(self) -> Dict[str, Any]:
        """Get performance metrics by query classification"""
        with self.lock:
            performance = {}
            
            for classification in self.response_times:
                times = self.response_times[classification]
                errors = self.error_patterns[classification]
                total_count = self.classification_accuracy.get(classification, 0) + errors
                
                if times:
                    performance[classification] = {
                        "avg_response_time": sum(times) / len(times),
                        "min_response_time": min(times),
                        "max_response_time": max(times),
                        "total_queries": total_count,
                        "error_count": errors,
                        "success_rate": (total_count - errors) / total_count if total_count > 0 else 0
                    }
            
            return performance
    
    def suggest_optimizations(self) -> List[str]:
        """Suggest optimizations based on analytics"""
        suggestions = []
        
        with self.lock:
            if not self.query_history:
                return ["Insufficient data for optimization suggestions"]
            
            # Check overall success rate
            total_queries = len(self.query_history)
            successful_queries = sum(1 for q in self.query_history if q['success'])
            success_rate = successful_queries / total_queries
            
            if success_rate < 0.8:
                suggestions.append(f"Overall success rate is {success_rate:.1%}. Consider improving error handling.")
            
            # Check response time performance
            avg_response_time = sum(q['response_time'] for q in self.query_history) / total_queries
            if avg_response_time > 5.0:
                suggestions.append(f"Average response time is {avg_response_time:.1f}s. Consider optimizing slow operations.")
            
            # Check for problematic classifications
            for classification, times in self.response_times.items():
                if times and len(times) > 5:  # Only analyze classifications with enough data
                    avg_time = sum(times) / len(times)
                    error_rate = self.error_patterns[classification] / len(times)
                    
                    if avg_time > 8.0:
                        suggestions.append(f"'{classification}' queries are slow (avg: {avg_time:.1f}s). Consider caching or optimization.")
                    
                    if error_rate > 0.2:
                        suggestions.append(f"'{classification}' queries have high error rate ({error_rate:.1%}). Review error handling.")
            
            # Check for common patterns that might benefit from optimization
            top_patterns = self.query_patterns.most_common(5)
            for pattern, count in top_patterns:
                if count > 10 and 'game_search' in pattern:
                    suggestions.append(f"Many game search queries detected. Consider database indexing optimization.")
                elif count > 10 and 'opening' in pattern:
                    suggestions.append(f"Many opening queries detected. Consider precomputing common opening data.")
        
        return suggestions if suggestions else ["System performance looks good!"]
    
    def log_analytics_summary(self):
        """Log a summary of current analytics"""
        analytics = self.get_global_analytics()
        performance = self.get_classification_performance()
        
        logger.info("=== RAG Query Analytics Summary ===")
        logger.info(f"Total queries: {analytics.get('total_queries', 0)}")
        logger.info(f"Success rate: {analytics.get('success_rate', 0):.1%}")
        logger.info(f"Average response time: {analytics.get('avg_response_time', 0):.2f}s")
        logger.info(f"Unique sessions: {analytics.get('unique_sessions', 0)}")
        
        if performance:
            logger.info("Performance by classification:")
            for classification, metrics in performance.items():
                logger.info(f"  {classification}: {metrics['success_rate']:.1%} success, {metrics['avg_response_time']:.2f}s avg")

# Global analytics instance
query_analytics = QueryAnalytics() 