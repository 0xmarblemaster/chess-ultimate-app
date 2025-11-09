"""
Relevance Scorer for Chess RAG System

Provides advanced scoring mechanisms for document relevance including:
- Multi-factor scoring (semantic, positional, tactical)
- Dynamic weighting based on query type and context
- Relevance feedback learning
- Score calibration across different query types
"""

import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

try:
    from .context_manager import ChessContext
except ImportError:
    from context_manager import ChessContext

try:
    from .performance_monitor import performance_monitor
except ImportError:
    from performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class RelevanceScore:
    """Detailed relevance scoring breakdown"""
    
    # Individual score components
    semantic_score: float = 0.0
    position_score: float = 0.0
    tactical_score: float = 0.0
    intent_score: float = 0.0
    freshness_score: float = 0.0
    user_feedback_score: float = 0.0
    
    # Final weighted score
    final_score: float = 0.0
    
    # Confidence and metadata
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'semantic_score': self.semantic_score,
            'position_score': self.position_score,
            'tactical_score': self.tactical_score,
            'intent_score': self.intent_score,
            'freshness_score': self.freshness_score,
            'user_feedback_score': self.user_feedback_score,
            'final_score': self.final_score,
            'confidence': self.confidence,
            'reasoning': self.reasoning
        }


class RelevanceScorer:
    """
    Advanced relevance scoring system for chess documents
    """
    
    def __init__(self):
        # Scoring weights for different query intents
        self.intent_weights = {
            'opening': {
                'semantic': 0.35,
                'position': 0.25,
                'tactical': 0.10,
                'intent': 0.20,
                'freshness': 0.05,
                'user_feedback': 0.05
            },
            'tactics': {
                'semantic': 0.25,
                'position': 0.15,
                'tactical': 0.35,
                'intent': 0.15,
                'freshness': 0.05,
                'user_feedback': 0.05
            },
            'strategy': {
                'semantic': 0.40,
                'position': 0.25,
                'tactical': 0.10,
                'intent': 0.15,
                'freshness': 0.05,
                'user_feedback': 0.05
            },
            'endgame': {
                'semantic': 0.30,
                'position': 0.35,
                'tactical': 0.15,
                'intent': 0.10,
                'freshness': 0.05,
                'user_feedback': 0.05
            },
            'analysis': {
                'semantic': 0.25,
                'position': 0.30,
                'tactical': 0.20,
                'intent': 0.15,
                'freshness': 0.05,
                'user_feedback': 0.05
            },
            'general': {
                'semantic': 0.50,
                'position': 0.15,
                'tactical': 0.10,
                'intent': 0.15,
                'freshness': 0.05,
                'user_feedback': 0.05
            }
        }
        
        # User feedback tracking
        self.feedback_data = defaultdict(list)  # document_id -> feedback scores
        self.feedback_lock = threading.Lock()
        
        # Score calibration data
        self.score_history = defaultdict(list)  # intent_type -> historical scores
        self.calibration_lock = threading.Lock()
        
        # Pattern recognition for scoring
        self.scoring_patterns = self._initialize_scoring_patterns()
    
    def _initialize_scoring_patterns(self) -> Dict[str, Dict[str, float]]:
        """Initialize patterns that boost scoring for different contexts"""
        return {
            'opening_indicators': {
                'development': 0.3,
                'castle': 0.2,
                'center control': 0.25,
                'tempo': 0.15,
                'initiative': 0.2,
                'opening principles': 0.35
            },
            'tactical_indicators': {
                'fork': 0.4,
                'pin': 0.35,
                'skewer': 0.3,
                'discovery': 0.3,
                'sacrifice': 0.25,
                'combination': 0.3,
                'attack': 0.2,
                'puzzle': 0.25
            },
            'strategic_indicators': {
                'plan': 0.3,
                'strategy': 0.35,
                'positional': 0.25,
                'structure': 0.2,
                'weakness': 0.25,
                'advantage': 0.2,
                'space': 0.15,
                'initiative': 0.2
            },
            'endgame_indicators': {
                'technique': 0.35,
                'conversion': 0.3,
                'opposition': 0.25,
                'zugzwang': 0.3,
                'breakthrough': 0.25,
                'promotion': 0.2,
                'king activity': 0.2,
                'pawn endgame': 0.3
            }
        }
    
    @performance_monitor.timer('relevance_scoring')
    def score_document(self, 
                      document: Dict[str, Any], 
                      query: str, 
                      context: ChessContext,
                      base_scores: Optional[Dict[str, float]] = None) -> RelevanceScore:
        """
        Calculate comprehensive relevance score for a document
        
        Args:
            document: Document to score
            query: Original user query
            context: Chess context from query
            base_scores: Pre-calculated base scores (semantic, position, tactical)
            
        Returns:
            Detailed relevance score breakdown
        """
        
        content = document.get('content', '')
        doc_id = document.get('id', '')
        
        score = RelevanceScore()
        
        # Use provided base scores or calculate new ones
        if base_scores:
            score.semantic_score = base_scores.get('semantic', 0.0)
            score.position_score = base_scores.get('position', 0.0)
            score.tactical_score = base_scores.get('tactical', 0.0)
        else:
            score.semantic_score = self._calculate_semantic_score(content, query)
            score.position_score = self._calculate_position_score(content, context)
            score.tactical_score = self._calculate_tactical_score(content, context)
        
        # Calculate additional scores
        score.intent_score = self._calculate_intent_score(content, context)
        score.freshness_score = self._calculate_freshness_score(document)
        score.user_feedback_score = self._get_user_feedback_score(doc_id)
        
        # Calculate weighted final score
        weights = self.intent_weights.get(context.intent_type, self.intent_weights['general'])
        
        score.final_score = (
            score.semantic_score * weights['semantic'] +
            score.position_score * weights['position'] +
            score.tactical_score * weights['tactical'] +
            score.intent_score * weights['intent'] +
            score.freshness_score * weights['freshness'] +
            score.user_feedback_score * weights['user_feedback']
        )
        
        # Apply query complexity adjustments
        score.final_score = self._adjust_for_complexity(score.final_score, context.query_complexity)
        
        # Calculate confidence
        score.confidence = self._calculate_confidence(score, context)
        
        # Generate reasoning
        score.reasoning = self._generate_reasoning(score, context, weights)
        
        # Calibrate score
        score.final_score = self._calibrate_score(score.final_score, context.intent_type)
        
        # Record score for future calibration
        self._record_score_for_calibration(context.intent_type, score.final_score)
        
        return score
    
    def _calculate_semantic_score(self, content: str, query: str) -> float:
        """Calculate semantic relevance score"""
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Simple word overlap scoring
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(content_words))
        base_score = overlap / len(query_words)
        
        # Boost for exact phrase matches
        if query_lower in content_lower:
            base_score += 0.3
        
        # Boost for important chess terms
        chess_terms = ['chess', 'move', 'position', 'game', 'strategy', 'tactic']
        term_boost = sum(0.05 for term in chess_terms if term in content_lower)
        
        return min(base_score + term_boost, 1.0)
    
    def _calculate_position_score(self, content: str, context: ChessContext) -> float:
        """Calculate position-specific relevance score"""
        if not context.current_fen:
            return 0.0
        
        content_lower = content.lower()
        score = 0.0
        
        # Position type relevance
        if context.position_type and context.position_type in content_lower:
            score += 0.4
        
        # Material balance relevance
        if context.material_balance:
            balance = context.material_balance.get('balance', 0)
            if abs(balance) > 3:  # Material imbalance
                if 'material' in content_lower or 'advantage' in content_lower:
                    score += 0.3
        
        # FEN-related content
        if 'fen' in content_lower or 'position' in content_lower:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_tactical_score(self, content: str, context: ChessContext) -> float:
        """Calculate tactical pattern relevance score"""
        if not context.tactical_patterns:
            return 0.0
        
        content_lower = content.lower()
        score = 0.0
        
        # Direct pattern matches
        for pattern in context.tactical_patterns:
            if pattern in content_lower:
                score += 0.4
        
        # General tactical relevance
        tactical_terms = ['tactic', 'combination', 'attack', 'sacrifice', 'puzzle']
        for term in tactical_terms:
            if term in content_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_intent_score(self, content: str, context: ChessContext) -> float:
        """Calculate intent-specific relevance score"""
        content_lower = content.lower()
        
        patterns = self.scoring_patterns.get(f"{context.intent_type}_indicators", {})
        score = 0.0
        
        for indicator, weight in patterns.items():
            if indicator.lower() in content_lower:
                score += weight
        
        return min(score, 1.0)
    
    def _calculate_freshness_score(self, document: Dict[str, Any]) -> float:
        """Calculate document freshness score"""
        # Simple implementation - in practice, you'd use document metadata
        # For now, assume all documents are equally fresh
        return 0.5
    
    def _get_user_feedback_score(self, document_id: str) -> float:
        """Get user feedback score for document"""
        with self.feedback_lock:
            feedback_scores = self.feedback_data.get(document_id, [])
            if not feedback_scores:
                return 0.5  # Neutral score for no feedback
            
            # Calculate average feedback with recency weighting
            recent_weight = 0.7
            old_weight = 0.3
            
            if len(feedback_scores) == 1:
                return feedback_scores[0]
            
            recent_scores = feedback_scores[-3:]  # Last 3 feedback scores
            old_scores = feedback_scores[:-3] if len(feedback_scores) > 3 else []
            
            recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0.5
            old_avg = sum(old_scores) / len(old_scores) if old_scores else 0.5
            
            return recent_avg * recent_weight + old_avg * old_weight
    
    def _adjust_for_complexity(self, score: float, complexity: str) -> float:
        """Adjust score based on query complexity"""
        adjustments = {
            'simple': 0.0,    # No adjustment for simple queries
            'medium': 0.05,   # Small boost for medium complexity
            'complex': 0.1    # Larger boost for complex queries
        }
        
        adjustment = adjustments.get(complexity, 0.0)
        return min(score + adjustment, 1.0)
    
    def _calculate_confidence(self, score: RelevanceScore, context: ChessContext) -> float:
        """Calculate confidence in the relevance score"""
        confidence_factors = []
        
        # High semantic score increases confidence
        if score.semantic_score > 0.7:
            confidence_factors.append(0.3)
        elif score.semantic_score > 0.4:
            confidence_factors.append(0.2)
        
        # Multiple scoring dimensions increase confidence
        non_zero_scores = sum(1 for s in [score.semantic_score, score.position_score, 
                                         score.tactical_score, score.intent_score] if s > 0.1)
        if non_zero_scores >= 3:
            confidence_factors.append(0.3)
        elif non_zero_scores >= 2:
            confidence_factors.append(0.2)
        
        # High intent confidence increases relevance confidence
        confidence_factors.append(context.confidence * 0.3)
        
        # User feedback availability increases confidence
        if score.user_feedback_score != 0.5:  # Not neutral
            confidence_factors.append(0.2)
        
        base_confidence = 0.5
        return min(base_confidence + sum(confidence_factors), 1.0)
    
    def _generate_reasoning(self, score: RelevanceScore, context: ChessContext, weights: Dict[str, float]) -> List[str]:
        """Generate human-readable reasoning for the score"""
        reasoning = []
        
        # Semantic reasoning
        if score.semantic_score > 0.6:
            reasoning.append(f"High semantic match ({score.semantic_score:.2f}) with query terms")
        elif score.semantic_score > 0.3:
            reasoning.append(f"Moderate semantic match ({score.semantic_score:.2f}) with query")
        
        # Position reasoning
        if score.position_score > 0.3 and context.current_fen:
            reasoning.append(f"Relevant to current position ({context.position_type})")
        
        # Tactical reasoning
        if score.tactical_score > 0.3 and context.tactical_patterns:
            patterns_str = ", ".join(context.tactical_patterns[:2])
            reasoning.append(f"Contains tactical patterns: {patterns_str}")
        
        # Intent reasoning
        if score.intent_score > 0.3:
            reasoning.append(f"Matches {context.intent_type} intent")
        
        # Feedback reasoning
        if score.user_feedback_score > 0.7:
            reasoning.append("Highly rated by previous users")
        elif score.user_feedback_score < 0.3:
            reasoning.append("Lower user ratings")
        
        # Overall reasoning
        if score.final_score > 0.8:
            reasoning.append("Excellent overall relevance")
        elif score.final_score > 0.6:
            reasoning.append("Good overall relevance")
        elif score.final_score < 0.3:
            reasoning.append("Limited relevance to query")
        
        return reasoning
    
    def _calibrate_score(self, score: float, intent_type: str) -> float:
        """Calibrate score based on historical performance"""
        with self.calibration_lock:
            historical_scores = self.score_history.get(intent_type, [])
            
            if len(historical_scores) < 10:
                return score  # Not enough data for calibration
            
            # Simple calibration: normalize based on historical distribution
            mean_score = np.mean(historical_scores)
            std_score = np.std(historical_scores)
            
            if std_score > 0:
                # Z-score normalization, then sigmoid to [0,1]
                z_score = (score - mean_score) / std_score
                calibrated = 1 / (1 + np.exp(-z_score))
                return calibrated
            
            return score
    
    def _record_score_for_calibration(self, intent_type: str, score: float):
        """Record score for future calibration"""
        with self.calibration_lock:
            self.score_history[intent_type].append(score)
            
            # Keep only recent scores for calibration
            max_history = 1000
            if len(self.score_history[intent_type]) > max_history:
                self.score_history[intent_type] = self.score_history[intent_type][-max_history:]
    
    def add_user_feedback(self, document_id: str, feedback_score: float, feedback_type: str = "relevance"):
        """
        Add user feedback for a document
        
        Args:
            document_id: Document identifier
            feedback_score: Score from 0.0 (not relevant) to 1.0 (highly relevant)
            feedback_type: Type of feedback (relevance, quality, etc.)
        """
        with self.feedback_lock:
            # Normalize feedback score
            normalized_score = max(0.0, min(1.0, feedback_score))
            
            self.feedback_data[document_id].append(normalized_score)
            
            # Keep only recent feedback
            max_feedback = 20
            if len(self.feedback_data[document_id]) > max_feedback:
                self.feedback_data[document_id] = self.feedback_data[document_id][-max_feedback:]
        
        logger.info(f"Added user feedback for document {document_id}: {normalized_score}")
    
    def get_scoring_statistics(self) -> Dict[str, Any]:
        """Get statistics about scoring performance"""
        with self.calibration_lock:
            stats = {}
            
            for intent_type, scores in self.score_history.items():
                if scores:
                    stats[intent_type] = {
                        'count': len(scores),
                        'mean': np.mean(scores),
                        'std': np.std(scores),
                        'min': np.min(scores),
                        'max': np.max(scores)
                    }
            
            return stats
    
    def get_feedback_statistics(self) -> Dict[str, Any]:
        """Get statistics about user feedback"""
        with self.feedback_lock:
            total_documents = len(self.feedback_data)
            total_feedback = sum(len(feedback) for feedback in self.feedback_data.values())
            
            if total_feedback > 0:
                all_scores = [score for feedback in self.feedback_data.values() for score in feedback]
                avg_feedback = np.mean(all_scores)
                
                return {
                    'documents_with_feedback': total_documents,
                    'total_feedback_count': total_feedback,
                    'average_feedback_score': avg_feedback,
                    'feedback_distribution': {
                        'high (>0.7)': sum(1 for s in all_scores if s > 0.7),
                        'medium (0.3-0.7)': sum(1 for s in all_scores if 0.3 <= s <= 0.7),
                        'low (<0.3)': sum(1 for s in all_scores if s < 0.3)
                    }
                }
            
            return {
                'documents_with_feedback': 0,
                'total_feedback_count': 0,
                'average_feedback_score': 0.0
            }


# Global relevance scorer instance
relevance_scorer = RelevanceScorer()

# Convenience function for scoring
def score_document_relevance(document: Dict[str, Any], 
                           query: str, 
                           context: ChessContext,
                           base_scores: Optional[Dict[str, float]] = None) -> RelevanceScore:
    """
    Convenience function to score document relevance
    
    Args:
        document: Document to score
        query: Original user query
        context: Chess context from query
        base_scores: Pre-calculated base scores
        
    Returns:
        Detailed relevance score
    """
    return relevance_scorer.score_document(document, query, context, base_scores) 