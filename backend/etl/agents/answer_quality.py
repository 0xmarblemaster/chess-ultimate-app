"""
Answer Quality Metrics for Chess RAG System

Provides comprehensive quality assessment for generated answers including:
- Accuracy metrics
- Completeness scoring
- Clarity and readability assessment
- Chess-specific quality indicators
- Contextual relevance evaluation
"""

import logging
import threading
import re
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
class QualityMetrics:
    """Comprehensive quality metrics for a generated answer"""
    
    # Core quality dimensions
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    clarity_score: float = 0.0
    relevance_score: float = 0.0
    chess_specificity_score: float = 0.0
    
    # Technical quality metrics
    coherence_score: float = 0.0
    factual_consistency_score: float = 0.0
    source_attribution_score: float = 0.0
    
    # Overall quality score
    overall_score: float = 0.0
    confidence: float = 0.0
    
    # Detailed metrics
    word_count: int = 0
    sentence_count: int = 0
    chess_terms_count: int = 0
    notation_accuracy: float = 0.0
    structure_score: float = 0.0
    
    # Quality flags
    quality_flags: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # Metadata
    assessment_timestamp: datetime = field(default_factory=datetime.now)
    assessment_method: str = "automated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'accuracy_score': self.accuracy_score,
            'completeness_score': self.completeness_score,
            'clarity_score': self.clarity_score,
            'relevance_score': self.relevance_score,
            'chess_specificity_score': self.chess_specificity_score,
            'coherence_score': self.coherence_score,
            'factual_consistency_score': self.factual_consistency_score,
            'source_attribution_score': self.source_attribution_score,
            'overall_score': self.overall_score,
            'confidence': self.confidence,
            'word_count': self.word_count,
            'sentence_count': self.sentence_count,
            'chess_terms_count': self.chess_terms_count,
            'notation_accuracy': self.notation_accuracy,
            'structure_score': self.structure_score,
            'quality_flags': self.quality_flags,
            'improvement_suggestions': self.improvement_suggestions,
            'assessment_timestamp': self.assessment_timestamp.isoformat(),
            'assessment_method': self.assessment_method
        }


class AnswerQualityAssessor:
    """
    Comprehensive answer quality assessment system for chess RAG
    """
    
    def __init__(self):
        # Quality assessment weights for different query types
        self.quality_weights = {
            'opening': {
                'accuracy': 0.25,
                'completeness': 0.20,
                'clarity': 0.15,
                'relevance': 0.20,
                'chess_specificity': 0.20
            },
            'tactics': {
                'accuracy': 0.35,
                'completeness': 0.15,
                'clarity': 0.15,
                'relevance': 0.15,
                'chess_specificity': 0.20
            },
            'strategy': {
                'accuracy': 0.20,
                'completeness': 0.25,
                'clarity': 0.20,
                'relevance': 0.20,
                'chess_specificity': 0.15
            },
            'endgame': {
                'accuracy': 0.30,
                'completeness': 0.20,
                'clarity': 0.15,
                'relevance': 0.15,
                'chess_specificity': 0.20
            },
            'analysis': {
                'accuracy': 0.25,
                'completeness': 0.25,
                'clarity': 0.20,
                'relevance': 0.15,
                'chess_specificity': 0.15
            },
            'general': {
                'accuracy': 0.20,
                'completeness': 0.20,
                'clarity': 0.25,
                'relevance': 0.25,
                'chess_specificity': 0.10
            }
        }
        
        # Chess-specific patterns and terminology
        self.chess_patterns = self._initialize_chess_patterns()
        
        # Quality tracking
        self.quality_history = defaultdict(list)  # intent_type -> quality scores
        self.quality_lock = threading.Lock()
        
        # User feedback integration
        self.user_ratings = defaultdict(list)  # answer_id -> user ratings
        self.rating_lock = threading.Lock()
    
    def _initialize_chess_patterns(self) -> Dict[str, Any]:
        """Initialize chess-specific patterns for quality assessment"""
        return {
            'notation_patterns': {
                'algebraic': re.compile(r'\b[NBRQK]?[a-h]?[1-8]?x?[a-h][1-8](?:[=][NBRQ])?[+#]?\b'),
                'coordinate': re.compile(r'\b[a-h][1-8]-[a-h][1-8]\b'),
                'fen': re.compile(r'\b[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8/]+ [wb] [KQkq-]+ [a-h][36] \d+ \d+\b')
            },
            'chess_terminology': {
                'basic': ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king', 'castle', 'check', 'checkmate'],
                'intermediate': ['fork', 'pin', 'skewer', 'discovered', 'tempo', 'initiative', 'development'],
                'advanced': ['zugzwang', 'opposition', 'deflection', 'decoy', 'clearance', 'interference'],
                'positional': ['weakness', 'outpost', 'blockade', 'space', 'control', 'structure'],
                'tactical': ['combination', 'sacrifice', 'attack', 'defense', 'counter-attack', 'tactic']
            },
            'quality_indicators': {
                'good_structure': ['first', 'second', 'then', 'because', 'therefore', 'however', 'moreover'],
                'explanation_words': ['why', 'how', 'when', 'where', 'what', 'reason', 'because'],
                'analysis_words': ['advantage', 'disadvantage', 'better', 'worse', 'strong', 'weak', 'evaluate']
            }
        }
    
    @performance_monitor.timer('answer_quality_assessment')
    def assess_answer_quality(self, 
                             answer: str, 
                             query: str, 
                             context: ChessContext,
                             retrieved_documents: List[Dict[str, Any]] = None,
                             answer_id: Optional[str] = None) -> QualityMetrics:
        """
        Comprehensive quality assessment of a generated answer
        
        Args:
            answer: Generated answer text
            query: Original user query
            context: Chess context from query
            retrieved_documents: Documents used for answer generation
            answer_id: Unique identifier for this answer
            
        Returns:
            Comprehensive quality metrics
        """
        
        metrics = QualityMetrics()
        
        # Basic text metrics
        metrics.word_count = len(answer.split())
        metrics.sentence_count = len([s for s in re.split(r'[.!?]+', answer) if s.strip()])
        
        # Core quality assessments
        metrics.accuracy_score = self._assess_accuracy(answer, context, retrieved_documents)
        metrics.completeness_score = self._assess_completeness(answer, query, context)
        metrics.clarity_score = self._assess_clarity(answer)
        metrics.relevance_score = self._assess_relevance(answer, query, context)
        metrics.chess_specificity_score = self._assess_chess_specificity(answer, context)
        
        # Technical quality assessments
        metrics.coherence_score = self._assess_coherence(answer)
        metrics.factual_consistency_score = self._assess_factual_consistency(answer, retrieved_documents)
        metrics.source_attribution_score = self._assess_source_attribution(answer, retrieved_documents)
        
        # Chess-specific assessments
        metrics.chess_terms_count = self._count_chess_terms(answer)
        metrics.notation_accuracy = self._assess_notation_accuracy(answer)
        metrics.structure_score = self._assess_structure(answer)
        
        # Calculate overall score
        weights = self.quality_weights.get(context.intent_type, self.quality_weights['general'])
        metrics.overall_score = (
            metrics.accuracy_score * weights['accuracy'] +
            metrics.completeness_score * weights['completeness'] +
            metrics.clarity_score * weights['clarity'] +
            metrics.relevance_score * weights['relevance'] +
            metrics.chess_specificity_score * weights['chess_specificity']
        )
        
        # Calculate confidence in assessment
        metrics.confidence = self._calculate_assessment_confidence(metrics, context)
        
        # Generate quality flags and suggestions
        metrics.quality_flags = self._generate_quality_flags(metrics, answer)
        metrics.improvement_suggestions = self._generate_improvement_suggestions(metrics, context, answer)
        
        # Integrate user feedback if available
        if answer_id:
            user_rating = self._get_user_rating(answer_id)
            if user_rating is not None:
                # Blend automated assessment with user feedback
                metrics.overall_score = metrics.overall_score * 0.7 + user_rating * 0.3
                metrics.quality_flags.append(f"user_rating_{user_rating:.1f}")
        
        # Record quality metrics for learning
        self._record_quality_metrics(context.intent_type, metrics)
        
        return metrics
    
    def _assess_accuracy(self, answer: str, context: ChessContext, retrieved_docs: List[Dict[str, Any]]) -> float:
        """Assess factual accuracy of the answer"""
        score = 0.5  # Base score
        
        # Check for chess notation accuracy
        notation_score = self._assess_notation_accuracy(answer)
        score += notation_score * 0.3
        
        # Check for factual consistency with retrieved documents
        if retrieved_docs:
            consistency_score = self._assess_factual_consistency(answer, retrieved_docs)
            score += consistency_score * 0.4
        
        # Check for common chess misconceptions
        misconception_penalty = self._check_common_misconceptions(answer)
        score -= misconception_penalty * 0.2
        
        # Check for specific claims that can be verified
        verifiable_claims_score = self._assess_verifiable_claims(answer, context)
        score += verifiable_claims_score * 0.1
        
        return min(max(score, 0.0), 1.0)
    
    def _assess_completeness(self, answer: str, query: str, context: ChessContext) -> float:
        """Assess how completely the answer addresses the query"""
        score = 0.0
        
        # Check if answer addresses main query intent
        if self._addresses_main_intent(answer, context):
            score += 0.4
        
        # Check for comprehensive coverage of topic
        coverage_score = self._assess_topic_coverage(answer, query, context)
        score += coverage_score * 0.3
        
        # Check for appropriate level of detail
        detail_score = self._assess_detail_level(answer, context.query_complexity)
        score += detail_score * 0.3
        
        return min(score, 1.0)
    
    def _assess_clarity(self, answer: str) -> float:
        """Assess clarity and readability of the answer"""
        score = 0.0
        
        # Sentence length assessment
        sentences = [s.strip() for s in re.split(r'[.!?]+', answer) if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_sentence_length <= 25:  # Optimal range
                score += 0.3
            elif avg_sentence_length < 40:  # Acceptable
                score += 0.2
        
        # Structure and organization
        structure_score = self._assess_structure(answer)
        score += structure_score * 0.4
        
        # Use of transition words and logical flow
        transition_score = self._assess_transitions(answer)
        score += transition_score * 0.3
        
        return min(score, 1.0)
    
    def _assess_relevance(self, answer: str, query: str, context: ChessContext) -> float:
        """Assess how relevant the answer is to the specific query"""
        answer_lower = answer.lower()
        query_lower = query.lower()
        
        score = 0.0
        
        # Direct query term matching
        query_words = set(query_lower.split())
        answer_words = set(answer_lower.split())
        
        if query_words:
            overlap = len(query_words.intersection(answer_words))
            score += (overlap / len(query_words)) * 0.3
        
        # Intent-specific relevance
        intent_relevance = self._assess_intent_relevance(answer, context)
        score += intent_relevance * 0.4
        
        # Context relevance (position, tactics, etc.)
        context_relevance = self._assess_context_relevance(answer, context)
        score += context_relevance * 0.3
        
        return min(score, 1.0)
    
    def _assess_chess_specificity(self, answer: str, context: ChessContext) -> float:
        """Assess how chess-specific and technically accurate the answer is"""
        score = 0.0
        
        # Chess terminology usage
        chess_terms_score = self._assess_chess_terminology_usage(answer)
        score += chess_terms_score * 0.4
        
        # Chess notation accuracy
        notation_score = self._assess_notation_accuracy(answer)
        score += notation_score * 0.3
        
        # Chess-specific concepts and principles
        concepts_score = self._assess_chess_concepts(answer, context)
        score += concepts_score * 0.3
        
        return min(score, 1.0)
    
    def _assess_coherence(self, answer: str) -> float:
        """Assess logical coherence and flow of the answer"""
        score = 0.5  # Base score
        
        # Check for logical connectors
        connectors = ['because', 'therefore', 'however', 'moreover', 'furthermore', 'consequently']
        connector_count = sum(1 for word in connectors if word in answer.lower())
        score += min(connector_count * 0.1, 0.3)
        
        # Check for contradictions (simple heuristic)
        contradiction_penalty = self._check_contradictions(answer)
        score -= contradiction_penalty
        
        # Check for topic consistency
        consistency_score = self._assess_topic_consistency(answer)
        score += consistency_score * 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def _assess_factual_consistency(self, answer: str, retrieved_docs: List[Dict[str, Any]]) -> float:
        """Assess consistency with source documents"""
        if not retrieved_docs:
            return 0.5  # Neutral score when no sources available
        
        # Simple implementation: check for contradiction with sources
        source_texts = [doc.get('content', '') for doc in retrieved_docs]
        combined_sources = ' '.join(source_texts).lower()
        answer_lower = answer.lower()
        
        # Look for alignment with source content
        answer_words = set(answer_lower.split())
        source_words = set(combined_sources.split())
        
        if answer_words:
            overlap = len(answer_words.intersection(source_words))
            alignment_score = overlap / len(answer_words)
            return min(alignment_score * 2, 1.0)  # Scale up the score
        
        return 0.5
    
    def _assess_source_attribution(self, answer: str, retrieved_docs: List[Dict[str, Any]]) -> float:
        """Assess how well the answer attributes information to sources"""
        if not retrieved_docs:
            return 1.0  # Perfect score if no attribution needed
        
        # Look for attribution indicators
        attribution_indicators = ['according to', 'as shown in', 'from the game', 'in the position', 'as demonstrated']
        attribution_count = sum(1 for indicator in attribution_indicators if indicator in answer.lower())
        
        # Score based on attribution relative to source count
        expected_attributions = min(len(retrieved_docs), 3)  # Don't expect too many
        if expected_attributions > 0:
            attribution_score = min(attribution_count / expected_attributions, 1.0)
        else:
            attribution_score = 1.0
        
        return attribution_score
    
    def _count_chess_terms(self, answer: str) -> int:
        """Count chess-specific terms in the answer"""
        answer_lower = answer.lower()
        count = 0
        
        for category, terms in self.chess_patterns['chess_terminology'].items():
            for term in terms:
                count += answer_lower.count(term.lower())
        
        return count
    
    def _assess_notation_accuracy(self, answer: str) -> float:
        """Assess accuracy of chess notation in the answer"""
        total_notation = 0
        correct_notation = 0
        
        # Check algebraic notation
        algebraic_matches = self.chess_patterns['notation_patterns']['algebraic'].findall(answer)
        total_notation += len(algebraic_matches)
        
        # Simple validation: check if notation follows basic patterns
        for notation in algebraic_matches:
            if self._is_valid_algebraic_notation(notation):
                correct_notation += 1
        
        # Check coordinate notation
        coordinate_matches = self.chess_patterns['notation_patterns']['coordinate'].findall(answer)
        total_notation += len(coordinate_matches)
        correct_notation += len(coordinate_matches)  # Assume coordinate notation is mostly correct
        
        if total_notation == 0:
            return 1.0  # No notation to validate
        
        return correct_notation / total_notation
    
    def _assess_structure(self, answer: str) -> float:
        """Assess structural organization of the answer"""
        score = 0.0
        
        # Check for clear opening
        first_sentence = answer.split('.')[0] if '.' in answer else answer
        if any(word in first_sentence.lower() for word in ['in this position', 'the best move', 'you should', 'consider']):
            score += 0.3
        
        # Check for logical progression
        structure_indicators = self.chess_patterns['quality_indicators']['good_structure']
        indicator_count = sum(1 for word in structure_indicators if word in answer.lower())
        score += min(indicator_count * 0.1, 0.4)
        
        # Check for conclusion or summary
        last_sentence = answer.split('.')[-1] if '.' in answer else answer
        if any(word in last_sentence.lower() for word in ['therefore', 'in conclusion', 'overall', 'remember']):
            score += 0.3
        
        return min(score, 1.0)
    
    def _is_valid_algebraic_notation(self, notation: str) -> bool:
        """Simple validation of algebraic chess notation"""
        # Remove check/checkmate symbols
        clean_notation = notation.rstrip('+#')
        
        # Basic pattern validation
        if len(clean_notation) < 2:
            return False
        
        # Check for valid file (a-h) and rank (1-8)
        if clean_notation[-2:].isalnum():
            file_char = clean_notation[-2]
            rank_char = clean_notation[-1]
            return file_char in 'abcdefgh' and rank_char in '12345678'
        
        return False
    
    def _addresses_main_intent(self, answer: str, context: ChessContext) -> bool:
        """Check if answer addresses the main intent of the query"""
        answer_lower = answer.lower()
        
        intent_keywords = {
            'opening': ['opening', 'development', 'principles', 'first moves'],
            'tactics': ['tactic', 'combination', 'attack', 'win material'],
            'strategy': ['plan', 'strategy', 'position', 'long-term'],
            'endgame': ['endgame', 'technique', 'king', 'pawn'],
            'analysis': ['analysis', 'evaluate', 'assessment', 'position']
        }
        
        keywords = intent_keywords.get(context.intent_type, [])
        return any(keyword in answer_lower for keyword in keywords)
    
    def _assess_topic_coverage(self, answer: str, query: str, context: ChessContext) -> float:
        """Assess how comprehensively the answer covers the topic"""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated topic modeling
        
        query_concepts = set(query.lower().split())
        answer_concepts = set(answer.lower().split())
        
        if not query_concepts:
            return 1.0
        
        coverage = len(query_concepts.intersection(answer_concepts)) / len(query_concepts)
        return min(coverage * 1.5, 1.0)  # Boost the score slightly
    
    def _assess_detail_level(self, answer: str, complexity: str) -> float:
        """Assess if detail level matches query complexity"""
        word_count = len(answer.split())
        
        expected_ranges = {
            'simple': (20, 100),
            'medium': (50, 200),
            'complex': (100, 400)
        }
        
        min_words, max_words = expected_ranges.get(complexity, (50, 200))
        
        if min_words <= word_count <= max_words:
            return 1.0
        elif word_count < min_words:
            return word_count / min_words
        else:
            # Penalty for being too verbose
            return max(0.5, 1.0 - (word_count - max_words) / max_words)
    
    def _assess_transitions(self, answer: str) -> float:
        """Assess use of transitions and logical flow"""
        transitions = ['first', 'second', 'then', 'next', 'finally', 'however', 'therefore', 'moreover']
        transition_count = sum(1 for word in transitions if word in answer.lower())
        
        sentences = len([s for s in re.split(r'[.!?]+', answer) if s.strip()])
        if sentences <= 1:
            return 1.0  # Single sentence doesn't need transitions
        
        expected_transitions = max(1, sentences // 3)
        return min(transition_count / expected_transitions, 1.0)
    
    def _assess_intent_relevance(self, answer: str, context: ChessContext) -> float:
        """Assess relevance to specific intent type"""
        # Use the chess-specific indicators
        patterns = self.chess_patterns.get('quality_indicators', {})
        
        if context.intent_type == 'tactics':
            tactical_words = ['attack', 'combination', 'sacrifice', 'win', 'capture', 'threat']
            return min(sum(0.2 for word in tactical_words if word in answer.lower()), 1.0)
        elif context.intent_type == 'opening':
            opening_words = ['development', 'center', 'castle', 'principles', 'tempo']
            return min(sum(0.2 for word in opening_words if word in answer.lower()), 1.0)
        # Add more intent-specific assessments
        
        return 0.5  # Default relevance
    
    def _assess_context_relevance(self, answer: str, context: ChessContext) -> float:
        """Assess relevance to chess context"""
        score = 0.0
        
        # Position type relevance
        if context.position_type and context.position_type in answer.lower():
            score += 0.5
        
        # Tactical pattern relevance
        if context.tactical_patterns:
            pattern_matches = sum(1 for pattern in context.tactical_patterns if pattern in answer.lower())
            score += min(pattern_matches * 0.25, 0.5)
        
        return min(score, 1.0)
    
    def _assess_chess_terminology_usage(self, answer: str) -> float:
        """Assess appropriate use of chess terminology"""
        answer_lower = answer.lower()
        
        # Count terminology usage by category
        basic_count = sum(1 for term in self.chess_patterns['chess_terminology']['basic'] if term in answer_lower)
        intermediate_count = sum(1 for term in self.chess_patterns['chess_terminology']['intermediate'] if term in answer_lower)
        advanced_count = sum(1 for term in self.chess_patterns['chess_terminology']['advanced'] if term in answer_lower)
        
        # Score based on terminology diversity and appropriateness
        total_terms = basic_count + intermediate_count + advanced_count
        word_count = len(answer.split())
        
        if word_count > 0:
            terminology_density = total_terms / word_count
            return min(terminology_density * 10, 1.0)  # Scale up the score
        
        return 0.0
    
    def _assess_chess_concepts(self, answer: str, context: ChessContext) -> float:
        """Assess use of appropriate chess concepts for the context"""
        answer_lower = answer.lower()
        score = 0.0
        
        # Intent-specific concept assessment
        if context.intent_type == 'tactics':
            tactical_concepts = ['fork', 'pin', 'skewer', 'discovered', 'sacrifice', 'combination']
            concept_count = sum(1 for concept in tactical_concepts if concept in answer_lower)
            score += min(concept_count * 0.25, 1.0)
        elif context.intent_type == 'strategy':
            strategic_concepts = ['plan', 'weakness', 'structure', 'space', 'initiative', 'development']
            concept_count = sum(1 for concept in strategic_concepts if concept in answer_lower)
            score += min(concept_count * 0.25, 1.0)
        
        return score
    
    def _check_common_misconceptions(self, answer: str) -> float:
        """Check for common chess misconceptions"""
        # This would contain known misconceptions
        # For now, return 0 (no misconceptions detected)
        return 0.0
    
    def _assess_verifiable_claims(self, answer: str, context: ChessContext) -> float:
        """Assess verifiable claims in the answer"""
        # This would check specific claims against chess databases
        # For now, return neutral score
        return 0.5
    
    def _check_contradictions(self, answer: str) -> float:
        """Check for internal contradictions"""
        # Simple contradiction detection
        contradiction_pairs = [
            (['good', 'best'], ['bad', 'worst']),
            (['safe', 'secure'], ['dangerous', 'risky']),
            (['attack', 'aggressive'], ['defend', 'passive'])
        ]
        
        answer_lower = answer.lower()
        contradiction_count = 0
        
        for positive_words, negative_words in contradiction_pairs:
            has_positive = any(word in answer_lower for word in positive_words)
            has_negative = any(word in answer_lower for word in negative_words)
            
            if has_positive and has_negative:
                # Check if they're in close proximity (might be comparison)
                words = answer_lower.split()
                for i, word in enumerate(words):
                    if word in positive_words:
                        nearby_words = words[max(0, i-5):i+6]
                        if any(neg_word in nearby_words for neg_word in negative_words):
                            # Only count as contradiction if no comparison words nearby
                            comparison_words = ['but', 'however', 'while', 'although', 'whereas']
                            if not any(comp_word in nearby_words for comp_word in comparison_words):
                                contradiction_count += 1
        
        return min(contradiction_count * 0.2, 0.5)
    
    def _assess_topic_consistency(self, answer: str) -> float:
        """Assess consistency of topic throughout the answer"""
        # Simple implementation: check if chess-related throughout
        sentences = [s.strip() for s in re.split(r'[.!?]+', answer) if s.strip()]
        
        if not sentences:
            return 1.0
        
        chess_sentences = 0
        for sentence in sentences:
            if any(term in sentence.lower() for category in self.chess_patterns['chess_terminology'].values() for term in category):
                chess_sentences += 1
        
        return chess_sentences / len(sentences) if sentences else 1.0
    
    def _calculate_assessment_confidence(self, metrics: QualityMetrics, context: ChessContext) -> float:
        """Calculate confidence in the quality assessment"""
        confidence_factors = []
        
        # High word count increases confidence
        if metrics.word_count > 50:
            confidence_factors.append(0.2)
        
        # Chess-specific content increases confidence
        if metrics.chess_terms_count > 3:
            confidence_factors.append(0.3)
        
        # Context confidence contributes
        confidence_factors.append(context.confidence * 0.3)
        
        # Consistent scores across dimensions increase confidence
        scores = [metrics.accuracy_score, metrics.completeness_score, metrics.clarity_score, 
                 metrics.relevance_score, metrics.chess_specificity_score]
        score_variance = np.var(scores)
        if score_variance < 0.1:  # Low variance indicates consistency
            confidence_factors.append(0.2)
        
        base_confidence = 0.5
        return min(base_confidence + sum(confidence_factors), 1.0)
    
    def _generate_quality_flags(self, metrics: QualityMetrics, answer: str) -> List[str]:
        """Generate quality flags based on assessment"""
        flags = []
        
        # Overall quality flags
        if metrics.overall_score > 0.8:
            flags.append("high_quality")
        elif metrics.overall_score < 0.4:
            flags.append("low_quality")
        
        # Specific dimension flags
        if metrics.accuracy_score < 0.3:
            flags.append("accuracy_concern")
        if metrics.completeness_score < 0.3:
            flags.append("incomplete")
        if metrics.clarity_score < 0.3:
            flags.append("unclear")
        if metrics.chess_specificity_score < 0.3:
            flags.append("low_chess_specificity")
        
        # Length flags
        if metrics.word_count < 20:
            flags.append("too_short")
        elif metrics.word_count > 300:
            flags.append("too_long")
        
        # Chess notation flags
        if metrics.notation_accuracy < 0.7:
            flags.append("notation_errors")
        
        return flags
    
    def _generate_improvement_suggestions(self, metrics: QualityMetrics, context: ChessContext, answer: str) -> List[str]:
        """Generate specific improvement suggestions"""
        suggestions = []
        
        # Accuracy improvements
        if metrics.accuracy_score < 0.5:
            suggestions.append("Verify chess facts and ensure notation accuracy")
        
        # Completeness improvements
        if metrics.completeness_score < 0.5:
            suggestions.append("Provide more comprehensive coverage of the topic")
        
        # Clarity improvements
        if metrics.clarity_score < 0.5:
            suggestions.append("Improve sentence structure and use clearer explanations")
        
        # Chess-specific improvements
        if metrics.chess_specificity_score < 0.5:
            suggestions.append("Include more chess-specific terminology and concepts")
        
        # Length-based suggestions
        if metrics.word_count < 30:
            suggestions.append("Provide more detailed explanation")
        elif metrics.word_count > 250:
            suggestions.append("Consider being more concise")
        
        # Intent-specific suggestions
        if context.intent_type == 'tactics' and 'combination' not in answer.lower():
            suggestions.append("Consider explaining the tactical combination")
        elif context.intent_type == 'opening' and 'development' not in answer.lower():
            suggestions.append("Mention piece development principles")
        
        return suggestions
    
    def _record_quality_metrics(self, intent_type: str, metrics: QualityMetrics):
        """Record quality metrics for learning and improvement"""
        with self.quality_lock:
            self.quality_history[intent_type].append(metrics.overall_score)
            
            # Keep only recent history
            max_history = 1000
            if len(self.quality_history[intent_type]) > max_history:
                self.quality_history[intent_type] = self.quality_history[intent_type][-max_history:]
    
    def _get_user_rating(self, answer_id: str) -> Optional[float]:
        """Get average user rating for an answer"""
        with self.rating_lock:
            ratings = self.user_ratings.get(answer_id, [])
            if ratings:
                return sum(ratings) / len(ratings)
            return None
    
    def add_user_rating(self, answer_id: str, rating: float, feedback_text: str = ""):
        """
        Add user rating for an answer
        
        Args:
            answer_id: Unique identifier for the answer
            rating: Rating from 0.0 to 1.0
            feedback_text: Optional textual feedback
        """
        with self.rating_lock:
            normalized_rating = max(0.0, min(1.0, rating))
            self.user_ratings[answer_id].append(normalized_rating)
            
            # Keep only recent ratings
            max_ratings = 10
            if len(self.user_ratings[answer_id]) > max_ratings:
                self.user_ratings[answer_id] = self.user_ratings[answer_id][-max_ratings:]
        
        logger.info(f"Added user rating for answer {answer_id}: {normalized_rating}")
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get quality assessment statistics"""
        with self.quality_lock:
            stats = {}
            
            for intent_type, scores in self.quality_history.items():
                if scores:
                    stats[intent_type] = {
                        'count': len(scores),
                        'mean': np.mean(scores),
                        'std': np.std(scores),
                        'min': np.min(scores),
                        'max': np.max(scores)
                    }
            
            return stats
    
    def get_user_rating_statistics(self) -> Dict[str, Any]:
        """Get user rating statistics"""
        with self.rating_lock:
            total_answers = len(self.user_ratings)
            total_ratings = sum(len(ratings) for ratings in self.user_ratings.values())
            
            if total_ratings > 0:
                all_ratings = [rating for ratings in self.user_ratings.values() for rating in ratings]
                avg_rating = np.mean(all_ratings)
                
                return {
                    'answers_with_ratings': total_answers,
                    'total_ratings_count': total_ratings,
                    'average_user_rating': avg_rating,
                    'rating_distribution': {
                        'excellent (>0.8)': sum(1 for r in all_ratings if r > 0.8),
                        'good (0.6-0.8)': sum(1 for r in all_ratings if 0.6 <= r <= 0.8),
                        'fair (0.4-0.6)': sum(1 for r in all_ratings if 0.4 <= r <= 0.6),
                        'poor (<0.4)': sum(1 for r in all_ratings if r < 0.4)
                    }
                }
            
            return {
                'answers_with_ratings': 0,
                'total_ratings_count': 0,
                'average_user_rating': 0.0
            }


# Global answer quality assessor instance
answer_quality_assessor = AnswerQualityAssessor()

# Convenience function for quality assessment
def assess_answer_quality(answer: str, 
                         query: str, 
                         context: ChessContext,
                         retrieved_documents: List[Dict[str, Any]] = None,
                         answer_id: Optional[str] = None) -> QualityMetrics:
    """
    Convenience function to assess answer quality
    
    Args:
        answer: Generated answer text
        query: Original user query
        context: Chess context from query
        retrieved_documents: Documents used for answer generation
        answer_id: Unique identifier for this answer
        
    Returns:
        Comprehensive quality metrics
    """
    return answer_quality_assessor.assess_answer_quality(
        answer, query, context, retrieved_documents, answer_id
    ) 