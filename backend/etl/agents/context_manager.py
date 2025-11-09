"""
Context Manager for Chess RAG System

Extracts and manages chess-specific context from user queries including:
- Chess position analysis
- Query intent classification
- Tactical pattern recognition
- Context preservation across conversations
"""

import re
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

try:
    from .performance_monitor import performance_monitor
except ImportError:
    from performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class ChessContext:
    """Represents extracted chess context from a query"""
    
    # Position Information
    current_fen: Optional[str] = None
    position_type: Optional[str] = None  # opening, middlegame, endgame
    material_balance: Optional[Dict[str, int]] = None
    
    # Query Intent
    intent_type: str = "general"  # opening, tactics, strategy, endgame, analysis
    confidence: float = 0.0
    
    # Tactical Patterns
    tactical_patterns: List[str] = field(default_factory=list)
    piece_activity: Dict[str, str] = field(default_factory=dict)
    
    # Context Metadata
    query_complexity: str = "simple"  # simple, medium, complex
    requires_calculation: bool = False
    requires_position_analysis: bool = False
    
    # Conversation Context
    previous_topics: List[str] = field(default_factory=list)
    session_focus: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for storage/transmission"""
        return {
            'current_fen': self.current_fen,
            'position_type': self.position_type,
            'material_balance': self.material_balance,
            'intent_type': self.intent_type,
            'confidence': self.confidence,
            'tactical_patterns': self.tactical_patterns,
            'piece_activity': self.piece_activity,
            'query_complexity': self.query_complexity,
            'requires_calculation': self.requires_calculation,
            'requires_position_analysis': self.requires_position_analysis,
            'previous_topics': self.previous_topics,
            'session_focus': self.session_focus
        }


class ContextManager:
    """
    Manages chess context extraction and preservation across conversations
    """
    
    def __init__(self):
        self.session_contexts: Dict[str, List[ChessContext]] = {}
        self.intent_patterns = self._initialize_intent_patterns()
        self.tactical_patterns = self._initialize_tactical_patterns()
        self.complexity_indicators = self._initialize_complexity_indicators()
        self.lock = threading.Lock()
        
        # Context preservation settings
        self.max_context_history = 10
        self.context_decay_hours = 24
    
    def _initialize_intent_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for intent classification"""
        return {
            'opening': [
                r'\b(opening|debut|start|begin)\b',
                r'\b(sicilian|french|caro.kann|english|queen.s gambit)\b',
                r'\bmove\s*(1|2|3|first|second|third)\b',
                r'\bdevelop|development\b',
                r'\bcastle|castling\b'
            ],
            'tactics': [
                r'\b(tactic|tactical|combination)\b',
                r'\b(fork|pin|skewer|discovery|deflection)\b',
                r'\b(sacrifice|attack|capture)\b',
                r'\b(mate|checkmate|mating)\b',
                r'\bpuzzle|problem\b'
            ],
            'strategy': [
                r'\b(strategy|strategic|plan|planning)\b',
                r'\b(pawn structure|weak square|outpost)\b',
                r'\b(initiative|space|control)\b',
                r'\b(long.term|positional)\b'
            ],
            'endgame': [
                r'\b(endgame|ending|end game)\b',
                r'\b(king and pawn|rook ending|queen ending)\b',
                r'\b(promotion|passed pawn)\b',
                r'\b(opposition|zugzwang|breakthrough)\b'
            ],
            'analysis': [
                r'\b(analyze|analysis|evaluate|evaluation)\b',
                r'\b(position|best move|continuation)\b',
                r'\b(engine|computer|stockfish)\b',
                r'\bwhy|explain|because\b'
            ]
        }
    
    def _initialize_tactical_patterns(self) -> Dict[str, List[str]]:
        """Initialize tactical pattern recognition"""
        return {
            'fork': [r'\bfork\b', r'\battack.*two\b', r'\bdouble.*attack\b'],
            'pin': [r'\bpin\b', r'\bpinned\b', r'\bcannot.*move\b'],
            'skewer': [r'\bskewer\b', r'\bthrough.*attack\b'],
            'discovery': [r'\bdiscovery\b', r'\bdiscovered\b', r'\buncover\b'],
            'deflection': [r'\bdeflection\b', r'\bdraw.*away\b'],
            'decoy': [r'\bdecoy\b', r'\blure\b', r'\bbait\b'],
            'clearance': [r'\bclearance\b', r'\bclear.*line\b'],
            'interference': [r'\binterference\b', r'\bblock.*line\b']
        }
    
    def _initialize_complexity_indicators(self) -> Dict[str, List[str]]:
        """Initialize query complexity indicators"""
        return {
            'simple': [
                r'^\w+\s*(move|play)\s*\w*\?*$',
                r'^(what|which|where).*\?$',
                r'^(good|bad|best).*\?$'
            ],
            'medium': [
                r'\b(why|how|explain)\b',
                r'\b(if|would|could|should)\b',
                r'\b(better|worse|compare)\b'
            ],
            'complex': [
                r'\b(analyze|evaluation|deep|complex)\b',
                r'\bmultiple.*move\b',
                r'\bvariation|line\b',
                r'\b(advantage|disadvantage).*because\b'
            ]
        }
    
    @performance_monitor.timer('context_extraction')
    def extract_context(self, query: str, current_fen: Optional[str] = None, 
                       session_id: Optional[str] = None) -> ChessContext:
        """
        Extract chess context from a user query
        
        Args:
            query: User's query text
            current_fen: Current chess position FEN
            session_id: Session identifier for context preservation
            
        Returns:
            ChessContext object with extracted information
        """
        query_lower = query.lower()
        context = ChessContext(current_fen=current_fen)
        
        # Extract intent
        intent, confidence = self._classify_intent(query_lower)
        context.intent_type = intent
        context.confidence = confidence
        
        # Extract tactical patterns
        context.tactical_patterns = self._extract_tactical_patterns(query_lower)
        
        # Determine complexity
        context.query_complexity = self._assess_complexity(query_lower)
        
        # Set analysis requirements
        context.requires_calculation = self._requires_calculation(query_lower)
        context.requires_position_analysis = self._requires_position_analysis(query_lower, current_fen)
        
        # Position analysis if FEN provided
        if current_fen:
            context.position_type = self._analyze_position_type(current_fen)
            context.material_balance = self._analyze_material_balance(current_fen)
        
        # Add session context if available
        if session_id:
            context = self._enrich_with_session_context(context, session_id)
            self._update_session_context(session_id, context)
        
        logger.info(f"Extracted context: intent={intent}({confidence:.2f}), "
                   f"complexity={context.query_complexity}, "
                   f"patterns={len(context.tactical_patterns)}")
        
        return context
    
    def _classify_intent(self, query: str) -> Tuple[str, float]:
        """Classify query intent with confidence score"""
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query, re.IGNORECASE))
                score += matches
            
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return "general", 0.5
        
        # Find best intent
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        max_score = sum(intent_scores.values())
        confidence = best_intent[1] / max_score if max_score > 0 else 0.5
        
        return best_intent[0], min(confidence, 1.0)
    
    def _extract_tactical_patterns(self, query: str) -> List[str]:
        """Extract mentioned tactical patterns"""
        found_patterns = []
        
        for pattern_name, pattern_regexes in self.tactical_patterns.items():
            for regex in pattern_regexes:
                if re.search(regex, query, re.IGNORECASE):
                    found_patterns.append(pattern_name)
                    break
        
        return found_patterns
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity level"""
        for complexity, patterns in self.complexity_indicators.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return complexity
        
        # Default complexity based on length and structure
        word_count = len(query.split())
        if word_count > 15:
            return "complex"
        elif word_count > 7:
            return "medium"
        else:
            return "simple"
    
    def _requires_calculation(self, query: str) -> bool:
        """Determine if query requires engine calculation"""
        calc_indicators = [
            r'\b(best|optimal|analyze|calculate)\b',
            r'\b(engine|computer|evaluation)\b',
            r'\b(move|continuation|variation)\b.*\b(find|show|give)\b',
            r'\b(tactical|combination|mate)\b'
        ]
        
        return any(re.search(pattern, query, re.IGNORECASE) for pattern in calc_indicators)
    
    def _requires_position_analysis(self, query: str, fen: Optional[str]) -> bool:
        """Determine if query requires position analysis"""
        if not fen:
            return False
        
        position_indicators = [
            r'\b(position|evaluate|assessment)\b',
            r'\b(advantage|better|worse)\b',
            r'\b(weak|strong).*\b(square|piece|pawn)\b',
            r'\b(structure|formation|setup)\b'
        ]
        
        return any(re.search(pattern, query, re.IGNORECASE) for pattern in position_indicators)
    
    def _analyze_position_type(self, fen: str) -> str:
        """Analyze position type from FEN"""
        try:
            # Simple heuristic based on piece count
            pieces = fen.split()[0].replace('/', '')
            piece_count = sum(1 for c in pieces if c.isupper() or c.islower())
            
            if piece_count >= 28:
                return "opening"
            elif piece_count >= 16:
                return "middlegame"
            else:
                return "endgame"
        except:
            return "unknown"
    
    def _analyze_material_balance(self, fen: str) -> Dict[str, int]:
        """Analyze material balance from FEN"""
        try:
            pieces = fen.split()[0].replace('/', '')
            
            piece_values = {
                'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9,
                'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9
            }
            
            white_material = sum(piece_values.get(p, 0) for p in pieces if p.isupper())
            black_material = sum(piece_values.get(p, 0) for p in pieces if p.islower())
            
            return {
                'white': white_material,
                'black': black_material,
                'balance': white_material - black_material
            }
        except:
            return {'white': 0, 'black': 0, 'balance': 0}
    
    def _enrich_with_session_context(self, context: ChessContext, session_id: str) -> ChessContext:
        """Enrich context with session history"""
        with self.lock:
            if session_id in self.session_contexts:
                recent_contexts = self.session_contexts[session_id][-self.max_context_history:]
                
                # Extract previous topics
                context.previous_topics = [ctx.intent_type for ctx in recent_contexts[-5:]]
                
                # Determine session focus
                if recent_contexts:
                    intent_counts = {}
                    for ctx in recent_contexts:
                        intent_counts[ctx.intent_type] = intent_counts.get(ctx.intent_type, 0) + 1
                    
                    if intent_counts:
                        context.session_focus = max(intent_counts.items(), key=lambda x: x[1])[0]
        
        return context
    
    def _update_session_context(self, session_id: str, context: ChessContext):
        """Update session context history"""
        with self.lock:
            if session_id not in self.session_contexts:
                self.session_contexts[session_id] = []
            
            self.session_contexts[session_id].append(context)
            
            # Cleanup old contexts
            cutoff_time = datetime.now() - timedelta(hours=self.context_decay_hours)
            # For simplicity, we'll just keep the latest contexts
            if len(self.session_contexts[session_id]) > self.max_context_history:
                self.session_contexts[session_id] = self.session_contexts[session_id][-self.max_context_history:]
    
    def get_session_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of session context"""
        with self.lock:
            if session_id not in self.session_contexts:
                return {'session_exists': False}
            
            contexts = self.session_contexts[session_id]
            if not contexts:
                return {'session_exists': True, 'context_count': 0}
            
            # Aggregate session statistics
            intent_counts = {}
            complexity_counts = {}
            tactical_patterns = set()
            
            for ctx in contexts:
                intent_counts[ctx.intent_type] = intent_counts.get(ctx.intent_type, 0) + 1
                complexity_counts[ctx.query_complexity] = complexity_counts.get(ctx.query_complexity, 0) + 1
                tactical_patterns.update(ctx.tactical_patterns)
            
            return {
                'session_exists': True,
                'context_count': len(contexts),
                'intent_distribution': intent_counts,
                'complexity_distribution': complexity_counts,
                'tactical_patterns_seen': list(tactical_patterns),
                'session_focus': contexts[-1].session_focus if contexts else None,
                'average_confidence': sum(ctx.confidence for ctx in contexts) / len(contexts)
            }
    
    def cleanup_old_sessions(self):
        """Clean up old session contexts"""
        # This would typically be called periodically
        # For now, we'll implement basic cleanup based on max sessions
        with self.lock:
            if len(self.session_contexts) > 100:  # Keep only 100 most recent sessions
                # Remove oldest sessions (this is a simple implementation)
                sessions_to_remove = list(self.session_contexts.keys())[:-100]
                for session_id in sessions_to_remove:
                    del self.session_contexts[session_id]
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """Get overall context extraction statistics"""
        with self.lock:
            total_sessions = len(self.session_contexts)
            total_contexts = sum(len(contexts) for contexts in self.session_contexts.values())
            
            if total_contexts == 0:
                return {
                    'total_sessions': total_sessions,
                    'total_contexts': total_contexts,
                    'average_contexts_per_session': 0
                }
            
            # Aggregate all contexts
            all_intents = []
            all_complexities = []
            all_patterns = []
            
            for contexts in self.session_contexts.values():
                for ctx in contexts:
                    all_intents.append(ctx.intent_type)
                    all_complexities.append(ctx.query_complexity)
                    all_patterns.extend(ctx.tactical_patterns)
            
            from collections import Counter
            
            return {
                'total_sessions': total_sessions,
                'total_contexts': total_contexts,
                'average_contexts_per_session': total_contexts / total_sessions,
                'intent_distribution': dict(Counter(all_intents)),
                'complexity_distribution': dict(Counter(all_complexities)),
                'tactical_patterns_frequency': dict(Counter(all_patterns))
            }


# Global context manager instance
context_manager = ContextManager()

# Convenience function for easy access
def extract_chess_context(query: str, current_fen: Optional[str] = None, 
                         session_id: Optional[str] = None) -> ChessContext:
    """
    Convenience function to extract chess context from a query
    
    Args:
        query: User's query text
        current_fen: Current chess position FEN
        session_id: Session identifier for context preservation
        
    Returns:
        ChessContext object with extracted information
    """
    return context_manager.extract_context(query, current_fen, session_id) 