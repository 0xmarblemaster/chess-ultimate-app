"""
Accuracy Tracking System for Chess RAG

Comprehensive system for tracking, measuring, and improving the accuracy
of the chess RAG system including:
- Accuracy metrics across different query types
- Learning from user feedback
- Performance tracking over time
- Accuracy improvement recommendations
"""

import logging
import threading
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

try:
    from .context_manager import ChessContext
except ImportError:
    from context_manager import ChessContext

try:
    from .answer_quality import QualityMetrics
except ImportError:
    from answer_quality import QualityMetrics

try:
    from .performance_monitor import performance_monitor
except ImportError:
    from performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class AccuracyMeasurement:
    """Single accuracy measurement for a query-answer pair"""
    
    # Identifiers
    measurement_id: str
    session_id: str
    query_id: str
    answer_id: str
    
    # Query and answer details
    query: str
    answer: str
    intent_type: str
    query_complexity: str
    
    # Accuracy scores
    automated_accuracy: float = 0.0
    user_accuracy_rating: Optional[float] = None
    expert_accuracy_rating: Optional[float] = None
    final_accuracy_score: float = 0.0
    
    # Supporting metrics
    quality_metrics: Optional[QualityMetrics] = None
    retrieval_accuracy: float = 0.0
    factual_accuracy: float = 0.0
    contextual_accuracy: float = 0.0
    
    # Accuracy flags and issues
    accuracy_issues: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'measurement_id': self.measurement_id,
            'session_id': self.session_id,
            'query_id': self.query_id,
            'answer_id': self.answer_id,
            'query': self.query,
            'answer': self.answer,
            'intent_type': self.intent_type,
            'query_complexity': self.query_complexity,
            'automated_accuracy': self.automated_accuracy,
            'user_accuracy_rating': self.user_accuracy_rating,
            'expert_accuracy_rating': self.expert_accuracy_rating,
            'final_accuracy_score': self.final_accuracy_score,
            'quality_metrics': self.quality_metrics.to_dict() if self.quality_metrics else None,
            'retrieval_accuracy': self.retrieval_accuracy,
            'factual_accuracy': self.factual_accuracy,
            'contextual_accuracy': self.contextual_accuracy,
            'accuracy_issues': self.accuracy_issues,
            'improvement_areas': self.improvement_areas,
            'timestamp': self.timestamp.isoformat(),
            'processing_time': self.processing_time,
            'confidence': self.confidence
        }


@dataclass
class AccuracyTrend:
    """Accuracy trend analysis over time"""
    
    intent_type: str
    time_period: str  # daily, weekly, monthly
    
    # Accuracy metrics over time
    accuracy_scores: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    
    # Trend statistics
    current_accuracy: float = 0.0
    previous_accuracy: float = 0.0
    accuracy_change: float = 0.0
    trend_direction: str = "stable"  # improving, declining, stable
    
    # Statistical measures
    mean_accuracy: float = 0.0
    std_accuracy: float = 0.0
    min_accuracy: float = 0.0
    max_accuracy: float = 0.0
    
    # Performance indicators
    total_queries: int = 0
    accuracy_target: float = 0.8
    target_achievement_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'intent_type': self.intent_type,
            'time_period': self.time_period,
            'current_accuracy': self.current_accuracy,
            'previous_accuracy': self.previous_accuracy,
            'accuracy_change': self.accuracy_change,
            'trend_direction': self.trend_direction,
            'mean_accuracy': self.mean_accuracy,
            'std_accuracy': self.std_accuracy,
            'min_accuracy': self.min_accuracy,
            'max_accuracy': self.max_accuracy,
            'total_queries': self.total_queries,
            'accuracy_target': self.accuracy_target,
            'target_achievement_rate': self.target_achievement_rate
        }


class AccuracyTracker:
    """
    Comprehensive accuracy tracking system for chess RAG
    """
    
    def __init__(self):
        # Accuracy measurements storage
        self.accuracy_measurements = {}  # measurement_id -> AccuracyMeasurement
        self.measurements_by_intent = defaultdict(list)  # intent_type -> [measurement_ids]
        self.measurements_by_session = defaultdict(list)  # session_id -> [measurement_ids]
        
        # Thread safety
        self.measurements_lock = threading.Lock()
        
        # Accuracy tracking configuration
        self.accuracy_weights = {
            'automated': 0.4,
            'user_feedback': 0.4,
            'expert_rating': 0.2
        }
        
        # Accuracy targets by intent type
        self.accuracy_targets = {
            'opening': 0.85,
            'tactics': 0.90,
            'strategy': 0.80,
            'endgame': 0.88,
            'analysis': 0.82,
            'general': 0.75
        }
        
        # Issue classification patterns
        self.accuracy_issue_patterns = self._initialize_issue_patterns()
        
        # Trend analysis cache
        self.trend_cache = {}
        self.trend_cache_expiry = {}
        self.trend_lock = threading.Lock()
    
    def _initialize_issue_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize patterns for identifying accuracy issues"""
        return {
            'factual_errors': {
                'patterns': ['incorrect', 'wrong', 'mistake', 'error'],
                'severity': 'high',
                'category': 'factual'
            },
            'notation_errors': {
                'patterns': ['invalid move', 'illegal', 'notation error'],
                'severity': 'high',
                'category': 'technical'
            },
            'incomplete_answer': {
                'patterns': ['incomplete', 'partial', 'missing'],
                'severity': 'medium',
                'category': 'completeness'
            },
            'unclear_explanation': {
                'patterns': ['unclear', 'confusing', 'hard to understand'],
                'severity': 'medium',
                'category': 'clarity'
            },
            'irrelevant_content': {
                'patterns': ['off-topic', 'irrelevant', 'not related'],
                'severity': 'medium',
                'category': 'relevance'
            },
            'outdated_information': {
                'patterns': ['outdated', 'old', 'deprecated'],
                'severity': 'low',
                'category': 'freshness'
            }
        }
    
    @performance_monitor.timer('accuracy_measurement')
    def measure_accuracy(self,
                        query: str,
                        answer: str,
                        context: ChessContext,
                        quality_metrics: Optional[QualityMetrics] = None,
                        retrieved_documents: List[Dict[str, Any]] = None,
                        session_id: str = "",
                        query_id: str = "",
                        answer_id: str = "") -> AccuracyMeasurement:
        """
        Comprehensive accuracy measurement for a query-answer pair
        
        Args:
            query: Original user query
            answer: Generated answer
            context: Chess context from query
            quality_metrics: Quality assessment results
            retrieved_documents: Documents used for answer generation
            session_id: Session identifier
            query_id: Query identifier
            answer_id: Answer identifier
            
        Returns:
            Comprehensive accuracy measurement
        """
        
        measurement_id = f"acc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{answer_id}"
        
        measurement = AccuracyMeasurement(
            measurement_id=measurement_id,
            session_id=session_id,
            query_id=query_id,
            answer_id=answer_id,
            query=query,
            answer=answer,
            intent_type=context.intent_type,
            query_complexity=context.query_complexity,
            quality_metrics=quality_metrics
        )
        
        # Calculate automated accuracy components
        measurement.retrieval_accuracy = self._assess_retrieval_accuracy(
            query, retrieved_documents, context
        )
        measurement.factual_accuracy = self._assess_factual_accuracy(
            answer, context, retrieved_documents
        )
        measurement.contextual_accuracy = self._assess_contextual_accuracy(
            answer, query, context
        )
        
        # Calculate overall automated accuracy
        measurement.automated_accuracy = self._calculate_automated_accuracy(
            measurement, quality_metrics
        )
        
        # Initial final score (will be updated when user feedback arrives)
        measurement.final_accuracy_score = measurement.automated_accuracy
        
        # Identify accuracy issues
        measurement.accuracy_issues = self._identify_accuracy_issues(
            answer, quality_metrics
        )
        
        # Generate improvement recommendations
        measurement.improvement_areas = self._generate_improvement_areas(
            measurement, context
        )
        
        # Calculate confidence in accuracy assessment
        measurement.confidence = self._calculate_accuracy_confidence(
            measurement, context
        )
        
        # Store measurement
        self._store_measurement(measurement)
        
        return measurement
    
    def _assess_retrieval_accuracy(self,
                                  query: str,
                                  retrieved_documents: List[Dict[str, Any]],
                                  context: ChessContext) -> float:
        """Assess accuracy of document retrieval"""
        if not retrieved_documents:
            return 0.5  # Neutral score when no documents retrieved
        
        score = 0.0
        
        # Check relevance of retrieved documents
        for doc in retrieved_documents[:3]:  # Check top 3 documents
            content = doc.get('content', '')
            
            # Query term relevance
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            
            if query_words:
                overlap = len(query_words.intersection(content_words))
                relevance = overlap / len(query_words)
                score += relevance * 0.3
            
            # Intent-specific relevance
            intent_relevance = self._check_intent_relevance(content, context)
            score += intent_relevance * 0.3
            
            # Chess-specific content check
            if self._contains_chess_content(content):
                score += 0.2
        
        # Normalize by number of documents checked
        return min(score / len(retrieved_documents[:3]), 1.0)
    
    def _assess_factual_accuracy(self,
                                answer: str,
                                context: ChessContext,
                                retrieved_documents: List[Dict[str, Any]]) -> float:
        """Assess factual accuracy of the answer"""
        score = 0.5  # Base score
        
        # Check consistency with retrieved documents
        if retrieved_documents:
            consistency_score = self._check_factual_consistency(answer, retrieved_documents)
            score += consistency_score * 0.3
        
        # Check chess notation accuracy
        notation_accuracy = self._check_notation_accuracy(answer)
        score += notation_accuracy * 0.3
        
        # Check for factual claims that can be verified
        verifiable_score = self._check_verifiable_claims(answer, context)
        score += verifiable_score * 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def _assess_contextual_accuracy(self,
                                   answer: str,
                                   query: str,
                                   context: ChessContext) -> float:
        """Assess how accurately the answer addresses the specific context"""
        score = 0.0
        
        # Query intent alignment
        intent_alignment = self._check_intent_alignment(answer, context)
        score += intent_alignment * 0.4
        
        # Position-specific accuracy (if applicable)
        if context.current_fen:
            position_accuracy = self._check_position_accuracy(answer, context)
            score += position_accuracy * 0.3
        
        # Tactical pattern accuracy (if applicable)
        if context.tactical_patterns:
            tactical_accuracy = self._check_tactical_accuracy(answer, context)
            score += tactical_accuracy * 0.3
        
        return min(score, 1.0)
    
    def _calculate_automated_accuracy(self,
                                     measurement: AccuracyMeasurement,
                                     quality_metrics: Optional[QualityMetrics]) -> float:
        """Calculate overall automated accuracy score"""
        
        # Base accuracy from individual components
        base_accuracy = (
            measurement.retrieval_accuracy * 0.3 +
            measurement.factual_accuracy * 0.4 +
            measurement.contextual_accuracy * 0.3
        )
        
        # Incorporate quality metrics if available
        if quality_metrics:
            quality_contribution = (
                quality_metrics.accuracy_score * 0.4 +
                quality_metrics.relevance_score * 0.3 +
                quality_metrics.chess_specificity_score * 0.3
            )
            
            # Blend base accuracy with quality metrics
            final_accuracy = base_accuracy * 0.6 + quality_contribution * 0.4
        else:
            final_accuracy = base_accuracy
        
        return min(max(final_accuracy, 0.0), 1.0)
    
    def _identify_accuracy_issues(self,
                                 answer: str,
                                 quality_metrics: Optional[QualityMetrics]) -> List[str]:
        """Identify potential accuracy issues"""
        issues = []
        
        # Check quality metrics for issues
        if quality_metrics:
            if quality_metrics.accuracy_score < 0.5:
                issues.append("low_automated_accuracy")
            if quality_metrics.factual_consistency_score < 0.5:
                issues.append("factual_inconsistency")
            if quality_metrics.notation_accuracy < 0.7:
                issues.append("notation_errors")
            if quality_metrics.relevance_score < 0.5:
                issues.append("low_relevance")
        
        # Check for specific issue patterns in the answer
        answer_lower = answer.lower()
        for issue_type, pattern_info in self.accuracy_issue_patterns.items():
            for pattern in pattern_info['patterns']:
                if pattern in answer_lower:
                    issues.append(issue_type)
                    break
        
        return list(set(issues))  # Remove duplicates
    
    def _generate_improvement_areas(self,
                                   measurement: AccuracyMeasurement,
                                   context: ChessContext) -> List[str]:
        """Generate specific areas for accuracy improvement"""
        improvements = []
        
        # Based on accuracy components
        if measurement.retrieval_accuracy < 0.6:
            improvements.append("improve_document_retrieval")
        if measurement.factual_accuracy < 0.6:
            improvements.append("enhance_factual_verification")
        if measurement.contextual_accuracy < 0.6:
            improvements.append("better_context_understanding")
        
        # Based on accuracy issues
        if "notation_errors" in measurement.accuracy_issues:
            improvements.append("validate_chess_notation")
        if "factual_inconsistency" in measurement.accuracy_issues:
            improvements.append("cross_reference_sources")
        if "low_relevance" in measurement.accuracy_issues:
            improvements.append("improve_query_understanding")
        
        # Intent-specific improvements
        if context.intent_type == 'tactics' and measurement.automated_accuracy < 0.7:
            improvements.append("enhance_tactical_analysis")
        elif context.intent_type == 'opening' and measurement.automated_accuracy < 0.7:
            improvements.append("improve_opening_knowledge")
        
        return improvements
    
    def _calculate_accuracy_confidence(self,
                                      measurement: AccuracyMeasurement,
                                      context: ChessContext) -> float:
        """Calculate confidence in the accuracy assessment"""
        confidence_factors = []
        
        # High individual component scores increase confidence
        if measurement.retrieval_accuracy > 0.7:
            confidence_factors.append(0.2)
        if measurement.factual_accuracy > 0.7:
            confidence_factors.append(0.3)
        if measurement.contextual_accuracy > 0.7:
            confidence_factors.append(0.2)
        
        # Context confidence contributes
        confidence_factors.append(context.confidence * 0.2)
        
        # Lack of accuracy issues increases confidence
        if not measurement.accuracy_issues:
            confidence_factors.append(0.1)
        
        base_confidence = 0.5
        return min(base_confidence + sum(confidence_factors), 1.0)
    
    def _store_measurement(self, measurement: AccuracyMeasurement):
        """Store accuracy measurement"""
        with self.measurements_lock:
            self.accuracy_measurements[measurement.measurement_id] = measurement
            self.measurements_by_intent[measurement.intent_type].append(measurement.measurement_id)
            self.measurements_by_session[measurement.session_id].append(measurement.measurement_id)
            
            # Limit storage size
            max_measurements = 10000
            if len(self.accuracy_measurements) > max_measurements:
                # Remove oldest measurements
                oldest_ids = sorted(self.accuracy_measurements.keys())[:1000]
                for old_id in oldest_ids:
                    self._remove_measurement(old_id)
    
    def _remove_measurement(self, measurement_id: str):
        """Remove a measurement from all storage"""
        if measurement_id in self.accuracy_measurements:
            measurement = self.accuracy_measurements[measurement_id]
            
            # Remove from intent tracking
            if measurement_id in self.measurements_by_intent[measurement.intent_type]:
                self.measurements_by_intent[measurement.intent_type].remove(measurement_id)
            
            # Remove from session tracking
            if measurement_id in self.measurements_by_session[measurement.session_id]:
                self.measurements_by_session[measurement.session_id].remove(measurement_id)
            
            # Remove main measurement
            del self.accuracy_measurements[measurement_id]
    
    def update_user_feedback(self,
                            measurement_id: str,
                            user_accuracy_rating: float,
                            feedback_text: str = ""):
        """
        Update measurement with user feedback
        
        Args:
            measurement_id: Measurement identifier
            user_accuracy_rating: User rating (0.0 to 1.0)
            feedback_text: Optional feedback text
        """
        with self.measurements_lock:
            if measurement_id in self.accuracy_measurements:
                measurement = self.accuracy_measurements[measurement_id]
                measurement.user_accuracy_rating = max(0.0, min(1.0, user_accuracy_rating))
                
                # Recalculate final accuracy score
                measurement.final_accuracy_score = self._calculate_final_accuracy(measurement)
                
                # Analyze feedback for additional issues
                if feedback_text:
                    additional_issues = self._analyze_feedback_text(feedback_text)
                    measurement.accuracy_issues.extend(additional_issues)
                    measurement.accuracy_issues = list(set(measurement.accuracy_issues))
                
                logger.info(f"Updated user feedback for {measurement_id}: {user_accuracy_rating}")
    
    def _calculate_final_accuracy(self, measurement: AccuracyMeasurement) -> float:
        """Calculate final accuracy score combining all available ratings"""
        scores = []
        weights = []
        
        # Automated accuracy
        scores.append(measurement.automated_accuracy)
        weights.append(self.accuracy_weights['automated'])
        
        # User feedback
        if measurement.user_accuracy_rating is not None:
            scores.append(measurement.user_accuracy_rating)
            weights.append(self.accuracy_weights['user_feedback'])
        
        # Expert rating
        if measurement.expert_accuracy_rating is not None:
            scores.append(measurement.expert_accuracy_rating)
            weights.append(self.accuracy_weights['expert_rating'])
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
            final_score = sum(score * weight for score, weight in zip(scores, normalized_weights))
        else:
            final_score = measurement.automated_accuracy
        
        return final_score
    
    def _analyze_feedback_text(self, feedback_text: str) -> List[str]:
        """Analyze feedback text for accuracy issues"""
        issues = []
        feedback_lower = feedback_text.lower()
        
        for issue_type, pattern_info in self.accuracy_issue_patterns.items():
            for pattern in pattern_info['patterns']:
                if pattern in feedback_lower:
                    issues.append(issue_type)
                    break
        
        return issues
    
    def get_accuracy_trend(self,
                          intent_type: str = "all",
                          time_period: str = "weekly") -> AccuracyTrend:
        """
        Get accuracy trend analysis
        
        Args:
            intent_type: Type of queries to analyze ("all" for all types)
            time_period: Time period for trend analysis
            
        Returns:
            Accuracy trend analysis
        """
        
        cache_key = f"{intent_type}_{time_period}"
        
        # Check cache
        with self.trend_lock:
            if (cache_key in self.trend_cache and 
                cache_key in self.trend_cache_expiry and
                datetime.now() < self.trend_cache_expiry[cache_key]):
                return self.trend_cache[cache_key]
        
        # Calculate trend
        trend = self._calculate_accuracy_trend(intent_type, time_period)
        
        # Cache result
        with self.trend_lock:
            self.trend_cache[cache_key] = trend
            self.trend_cache_expiry[cache_key] = datetime.now() + timedelta(hours=1)
        
        return trend
    
    def _calculate_accuracy_trend(self, intent_type: str, time_period: str) -> AccuracyTrend:
        """Calculate accuracy trend analysis"""
        trend = AccuracyTrend(intent_type=intent_type, time_period=time_period)
        
        # Get relevant measurements
        measurements = self._get_measurements_for_trend(intent_type, time_period)
        
        if not measurements:
            return trend
        
        # Extract accuracy scores and timestamps
        scores = [m.final_accuracy_score for m in measurements]
        timestamps = [m.timestamp for m in measurements]
        
        trend.accuracy_scores = scores
        trend.timestamps = timestamps
        trend.total_queries = len(measurements)
        
        # Calculate statistics
        trend.mean_accuracy = np.mean(scores)
        trend.std_accuracy = np.std(scores)
        trend.min_accuracy = np.min(scores)
        trend.max_accuracy = np.max(scores)
        
        # Calculate current and previous accuracy
        mid_point = len(scores) // 2
        if mid_point > 0:
            trend.previous_accuracy = np.mean(scores[:mid_point])
            trend.current_accuracy = np.mean(scores[mid_point:])
            trend.accuracy_change = trend.current_accuracy - trend.previous_accuracy
            
            # Determine trend direction
            if abs(trend.accuracy_change) < 0.02:
                trend.trend_direction = "stable"
            elif trend.accuracy_change > 0:
                trend.trend_direction = "improving"
            else:
                trend.trend_direction = "declining"
        else:
            trend.current_accuracy = trend.mean_accuracy
            trend.previous_accuracy = trend.mean_accuracy
        
        # Calculate target achievement rate
        target = self.accuracy_targets.get(intent_type, 0.8)
        trend.accuracy_target = target
        above_target = sum(1 for score in scores if score >= target)
        trend.target_achievement_rate = above_target / len(scores)
        
        return trend
    
    def _get_measurements_for_trend(self, intent_type: str, time_period: str) -> List[AccuracyMeasurement]:
        """Get measurements for trend analysis"""
        # Calculate time window
        now = datetime.now()
        if time_period == "daily":
            start_time = now - timedelta(days=7)  # Last 7 days
        elif time_period == "weekly":
            start_time = now - timedelta(weeks=8)  # Last 8 weeks
        elif time_period == "monthly":
            start_time = now - timedelta(days=180)  # Last 6 months
        else:
            start_time = now - timedelta(days=30)  # Default: last month
        
        measurements = []
        
        with self.measurements_lock:
            if intent_type == "all":
                # Get all measurements
                for measurement in self.accuracy_measurements.values():
                    if measurement.timestamp >= start_time:
                        measurements.append(measurement)
            else:
                # Get measurements for specific intent type
                measurement_ids = self.measurements_by_intent.get(intent_type, [])
                for measurement_id in measurement_ids:
                    if measurement_id in self.accuracy_measurements:
                        measurement = self.accuracy_measurements[measurement_id]
                        if measurement.timestamp >= start_time:
                            measurements.append(measurement)
        
        # Sort by timestamp
        measurements.sort(key=lambda m: m.timestamp)
        
        return measurements
    
    def get_accuracy_statistics(self) -> Dict[str, Any]:
        """Get comprehensive accuracy statistics"""
        with self.measurements_lock:
            stats = {
                'total_measurements': len(self.accuracy_measurements),
                'by_intent_type': {},
                'overall_accuracy': 0.0,
                'accuracy_distribution': {},
                'common_issues': {},
                'improvement_areas': {}
            }
            
            if not self.accuracy_measurements:
                return stats
            
            # Overall statistics
            all_scores = [m.final_accuracy_score for m in self.accuracy_measurements.values()]
            stats['overall_accuracy'] = np.mean(all_scores)
            
            # Accuracy distribution
            stats['accuracy_distribution'] = {
                'excellent (>0.9)': sum(1 for s in all_scores if s > 0.9),
                'good (0.8-0.9)': sum(1 for s in all_scores if 0.8 <= s <= 0.9),
                'fair (0.6-0.8)': sum(1 for s in all_scores if 0.6 <= s <= 0.8),
                'poor (<0.6)': sum(1 for s in all_scores if s < 0.6)
            }
            
            # By intent type
            for intent_type, measurement_ids in self.measurements_by_intent.items():
                measurements = [self.accuracy_measurements[mid] for mid in measurement_ids 
                              if mid in self.accuracy_measurements]
                
                if measurements:
                    scores = [m.final_accuracy_score for m in measurements]
                    stats['by_intent_type'][intent_type] = {
                        'count': len(measurements),
                        'mean_accuracy': np.mean(scores),
                        'std_accuracy': np.std(scores),
                        'target': self.accuracy_targets.get(intent_type, 0.8),
                        'target_achievement': sum(1 for s in scores 
                                                if s >= self.accuracy_targets.get(intent_type, 0.8)) / len(scores)
                    }
            
            # Common issues
            all_issues = []
            all_improvements = []
            for measurement in self.accuracy_measurements.values():
                all_issues.extend(measurement.accuracy_issues)
                all_improvements.extend(measurement.improvement_areas)
            
            # Count issue frequency
            from collections import Counter
            issue_counts = Counter(all_issues)
            improvement_counts = Counter(all_improvements)
            
            stats['common_issues'] = dict(issue_counts.most_common(10))
            stats['improvement_areas'] = dict(improvement_counts.most_common(10))
            
            return stats
    
    # Helper methods for accuracy assessment
    def _check_intent_relevance(self, content: str, context: ChessContext) -> float:
        """Check if content is relevant to query intent"""
        content_lower = content.lower()
        
        intent_keywords = {
            'opening': ['opening', 'development', 'principles'],
            'tactics': ['tactic', 'combination', 'attack'],
            'strategy': ['strategy', 'plan', 'position'],
            'endgame': ['endgame', 'technique', 'king'],
            'analysis': ['analysis', 'evaluate', 'position']
        }
        
        keywords = intent_keywords.get(context.intent_type, [])
        matches = sum(1 for keyword in keywords if keyword in content_lower)
        
        return min(matches / len(keywords) if keywords else 0, 1.0)
    
    def _contains_chess_content(self, content: str) -> bool:
        """Check if content contains chess-related information"""
        chess_indicators = ['chess', 'move', 'position', 'game', 'piece', 'board']
        content_lower = content.lower()
        
        return any(indicator in content_lower for indicator in chess_indicators)
    
    def _check_factual_consistency(self, answer: str, documents: List[Dict[str, Any]]) -> float:
        """Check factual consistency with source documents"""
        if not documents:
            return 0.5
        
        answer_lower = answer.lower()
        source_content = ' '.join(doc.get('content', '') for doc in documents).lower()
        
        # Simple consistency check based on word overlap
        answer_words = set(answer_lower.split())
        source_words = set(source_content.split())
        
        if not answer_words:
            return 0.5
        
        overlap = len(answer_words.intersection(source_words))
        consistency = overlap / len(answer_words)
        
        return min(consistency * 2, 1.0)  # Scale up the score
    
    def _check_notation_accuracy(self, answer: str) -> float:
        """Check chess notation accuracy in answer"""
        import re
        
        # Find chess moves in algebraic notation
        move_pattern = re.compile(r'\b[NBRQK]?[a-h]?[1-8]?x?[a-h][1-8](?:[=][NBRQ])?[+#]?\b')
        moves = move_pattern.findall(answer)
        
        if not moves:
            return 1.0  # No notation to check
        
        # Simple validation - check format
        valid_moves = 0
        for move in moves:
            # Basic format validation
            clean_move = move.rstrip('+#')
            if len(clean_move) >= 2:
                file_char = clean_move[-2]
                rank_char = clean_move[-1]
                if file_char in 'abcdefgh' and rank_char in '12345678':
                    valid_moves += 1
        
        return valid_moves / len(moves)
    
    def _check_verifiable_claims(self, answer: str, context: ChessContext) -> float:
        """Check verifiable claims in the answer"""
        # This would check against chess databases in a real implementation
        # For now, return neutral score
        return 0.5
    
    def _check_intent_alignment(self, answer: str, context: ChessContext) -> float:
        """Check if answer aligns with query intent"""
        return self._check_intent_relevance(answer, context)
    
    def _check_position_accuracy(self, answer: str, context: ChessContext) -> float:
        """Check position-specific accuracy"""
        if not context.current_fen:
            return 1.0
        
        # Simple check: mention of position-related terms
        position_terms = ['position', 'board', 'fen', context.position_type]
        answer_lower = answer.lower()
        
        matches = sum(1 for term in position_terms if term and term.lower() in answer_lower)
        return min(matches / len([t for t in position_terms if t]), 1.0)
    
    def _check_tactical_accuracy(self, answer: str, context: ChessContext) -> float:
        """Check tactical pattern accuracy"""
        if not context.tactical_patterns:
            return 1.0
        
        answer_lower = answer.lower()
        pattern_matches = sum(1 for pattern in context.tactical_patterns if pattern in answer_lower)
        
        return min(pattern_matches / len(context.tactical_patterns), 1.0)


# Global accuracy tracker instance
accuracy_tracker = AccuracyTracker()

# Convenience functions
def measure_query_accuracy(query: str,
                          answer: str,
                          context: ChessContext,
                          quality_metrics: Optional[QualityMetrics] = None,
                          retrieved_documents: List[Dict[str, Any]] = None,
                          session_id: str = "",
                          query_id: str = "",
                          answer_id: str = "") -> AccuracyMeasurement:
    """
    Convenience function to measure accuracy
    
    Args:
        query: Original user query
        answer: Generated answer
        context: Chess context from query
        quality_metrics: Quality assessment results
        retrieved_documents: Documents used for answer generation
        session_id: Session identifier
        query_id: Query identifier
        answer_id: Answer identifier
        
    Returns:
        Accuracy measurement
    """
    return accuracy_tracker.measure_accuracy(
        query, answer, context, quality_metrics, retrieved_documents,
        session_id, query_id, answer_id
    )

def add_user_accuracy_feedback(measurement_id: str,
                              user_rating: float,
                              feedback_text: str = ""):
    """
    Convenience function to add user accuracy feedback
    
    Args:
        measurement_id: Measurement identifier
        user_rating: User accuracy rating (0.0 to 1.0)
        feedback_text: Optional feedback text
    """
    accuracy_tracker.update_user_feedback(measurement_id, user_rating, feedback_text) 