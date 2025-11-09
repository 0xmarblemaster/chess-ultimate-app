"""
Enhanced Retriever for Chess RAG System

Provides context-aware document retrieval using chess position context,
query intent, and multi-modal search capabilities.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

try:
    from .context_manager import ChessContext
except ImportError:
    from context_manager import ChessContext

try:
    from .performance_monitor import performance_monitor
except ImportError:
    from performance_monitor import performance_monitor

try:
    from .cache_manager import query_cache
except ImportError:
    from cache_manager import query_cache

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Represents a single retrieval result with enhanced metadata"""
    
    document_id: str
    content: str
    relevance_score: float
    context_relevance: float
    position_relevance: float
    tactical_relevance: float
    
    # Metadata
    document_type: str = "unknown"  # opening, tactics, strategy, endgame, game
    difficulty_level: str = "intermediate"  # beginner, intermediate, advanced
    chess_concepts: List[str] = None
    
    def __post_init__(self):
        if self.chess_concepts is None:
            self.chess_concepts = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'document_id': self.document_id,
            'content': self.content,
            'relevance_score': self.relevance_score,
            'context_relevance': self.context_relevance,
            'position_relevance': self.position_relevance,
            'tactical_relevance': self.tactical_relevance,
            'document_type': self.document_type,
            'difficulty_level': self.difficulty_level,
            'chess_concepts': self.chess_concepts
        }


class EnhancedRetriever:
    """
    Enhanced document retriever with context-aware capabilities
    """
    
    def __init__(self, weaviate_client, base_retriever):
        """
        Initialize enhanced retriever
        
        Args:
            weaviate_client: Weaviate client instance
            base_retriever: Original retriever instance for fallback
        """
        self.weaviate_client = weaviate_client
        self.base_retriever = base_retriever
        
        # Retrieval weights for different context types
        self.context_weights = {
            'opening': {
                'semantic': 0.4,
                'position': 0.3,
                'tactical': 0.1,
                'document_type': 0.2
            },
            'tactics': {
                'semantic': 0.3,
                'position': 0.2,
                'tactical': 0.4,
                'document_type': 0.1
            },
            'strategy': {
                'semantic': 0.5,
                'position': 0.3,
                'tactical': 0.1,
                'document_type': 0.1
            },
            'endgame': {
                'semantic': 0.4,
                'position': 0.4,
                'tactical': 0.1,
                'document_type': 0.1
            },
            'analysis': {
                'semantic': 0.3,
                'position': 0.4,
                'tactical': 0.2,
                'document_type': 0.1
            },
            'general': {
                'semantic': 0.7,
                'position': 0.1,
                'tactical': 0.1,
                'document_type': 0.1
            }
        }
        
        # Document type mappings
        self.document_type_keywords = {
            'opening': ['opening', 'debut', 'development', 'castle', 'gambit'],
            'tactics': ['tactic', 'puzzle', 'combination', 'attack', 'sacrifice'],
            'strategy': ['strategy', 'plan', 'positional', 'structure', 'weakness'],
            'endgame': ['endgame', 'ending', 'promotion', 'opposition', 'technique'],
            'game': ['game', 'match', 'tournament', 'player', 'move']
        }
    
    @performance_monitor.timer('enhanced_retrieval')
    def retrieve_documents(self, 
                          query: str, 
                          context: ChessContext, 
                          limit: int = 10,
                          min_relevance: float = 0.3) -> List[RetrievalResult]:
        """
        Retrieve documents using enhanced context-aware search
        
        Args:
            query: User query text
            context: Extracted chess context
            limit: Maximum number of documents to retrieve
            min_relevance: Minimum relevance score threshold
            
        Returns:
            List of enhanced retrieval results
        """
        
        # Check cache first
        cache_key = f"enhanced_{hash(query)}_{hash(str(context.to_dict()))}"
        cached_results = query_cache.get(cache_key)
        if cached_results is not None:
            logger.info(f"Retrieved {len(cached_results)} documents from cache")
            return [RetrievalResult(**result) for result in cached_results]
        
        try:
            # Multi-modal retrieval
            results = []
            
            # 1. Semantic search
            semantic_results = self._semantic_search(query, limit * 2)
            
            # 2. Position-aware search (if FEN available)
            position_results = []
            if context.current_fen and context.requires_position_analysis:
                position_results = self._position_aware_search(context.current_fen, context.position_type, limit)
            
            # 3. Tactical pattern search
            tactical_results = []
            if context.tactical_patterns:
                tactical_results = self._tactical_pattern_search(context.tactical_patterns, limit)
            
            # 4. Intent-based search
            intent_results = self._intent_based_search(context.intent_type, query, limit)
            
            # Combine and score results
            all_results = self._combine_and_score_results(
                semantic_results, position_results, tactical_results, intent_results,
                context, limit, min_relevance
            )
            
            # Cache results
            serializable_results = [result.to_dict() for result in all_results]
            query_cache.set(cache_key, serializable_results)
            
            logger.info(f"Enhanced retrieval found {len(all_results)} relevant documents")
            return all_results
            
        except Exception as e:
            logger.error(f"Enhanced retrieval failed: {e}")
            # Fallback to base retriever
            return self._fallback_retrieval(query, limit)
    
    def _semantic_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform semantic search using base retriever"""
        try:
            # Use base retriever's semantic search with correct method name
            base_results = self.base_retriever.retrieve_semantic(query, k=limit)
            
            # Convert format to match expected format
            results = []
            if base_results.get('documents'):
                for i, doc in enumerate(base_results['documents']):
                    results.append({
                        'document_id': f"semantic_{i}",
                        'content': doc.get('content', str(doc)),
                        'metadata': doc.get('metadata', {}),
                        'semantic_score': 0.8 - (i * 0.05)  # Simulated scoring
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Fallback: Try direct FEN search if the query contains a FEN
            return self._fallback_fen_search(query, limit)
    
    def _position_aware_search(self, fen: str, position_type: str, limit: int) -> List[Dict[str, Any]]:
        """Search for documents relevant to the chess position"""
        try:
            # Create position-specific query
            position_query = f"chess position {position_type}"
            
            # Add material imbalance context if significant
            # This is a simplified implementation
            if position_type == "endgame":
                position_query += " king pawn endgame technique"
            elif position_type == "opening":
                position_query += " development principles castle"
            elif position_type == "middlegame":
                position_query += " attack defense tactical"
            
            # Search with position context
            results = self._search_weaviate(position_query, limit)
            
            for result in results:
                result['position_score'] = self._calculate_position_relevance(
                    result['content'], fen, position_type
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Position-aware search failed: {e}")
            return []
    
    def _tactical_pattern_search(self, patterns: List[str], limit: int) -> List[Dict[str, Any]]:
        """Search for documents about specific tactical patterns"""
        try:
            results = []
            
            for pattern in patterns[:3]:  # Limit to top 3 patterns
                pattern_query = f"chess tactics {pattern} pattern"
                pattern_results = self._search_weaviate(pattern_query, limit // len(patterns) + 1)
                
                for result in pattern_results:
                    result['tactical_score'] = self._calculate_tactical_relevance(
                        result['content'], patterns
                    )
                    results.append(result)
            
            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for result in results:
                doc_id = result['document_id']
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    unique_results.append(result)
            
            return unique_results[:limit]
            
        except Exception as e:
            logger.error(f"Tactical pattern search failed: {e}")
            return []
    
    def _intent_based_search(self, intent: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search based on query intent"""
        try:
            # Enhance query with intent-specific terms
            intent_terms = {
                'opening': 'opening principles development',
                'tactics': 'tactical combination puzzle',
                'strategy': 'strategic planning positional',
                'endgame': 'endgame technique conversion',
                'analysis': 'position evaluation analysis'
            }
            
            enhanced_query = f"{query} {intent_terms.get(intent, '')}"
            results = self._search_weaviate(enhanced_query, limit)
            
            for result in results:
                result['intent_score'] = self._calculate_intent_relevance(
                    result['content'], intent
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Intent-based search failed: {e}")
            return []
    
    def _search_weaviate(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform actual Weaviate search"""
        try:
            # Use the correct Weaviate v4 client API
            collection = self.weaviate_client.collections.get("ChessGame")
            search_results = collection.query.near_text(
                query=query,
                limit=limit
            )
            
            results = []
            if search_results and search_results.objects:
                for i, obj in enumerate(search_results.objects):
                    props = obj.properties
                    
                    # Create comprehensive content string that includes ELO data
                    white_player = props.get('white_player', 'Unknown')
                    black_player = props.get('black_player', 'Unknown')
                    white_elo = props.get('white_elo', 'N/A')
                    black_elo = props.get('black_elo', 'N/A')
                    event = props.get('event', '')
                    result = props.get('result', '')
                    eco = props.get('eco', '')
                    opening = props.get('opening', '')
                    
                    content_parts = [
                        f"Game: {white_player} vs {black_player}",
                        f"ELO Ratings: White: {white_elo}, Black: {black_elo}"
                    ]
                    if event:
                        content_parts.append(f"Event: {event}")
                    if result:
                        content_parts.append(f"Result: {result}")
                    if eco:
                        content_parts.append(f"ECO: {eco}")
                    if opening:
                        content_parts.append(f"Opening: {opening}")
                    
                    moves = props.get('pgn_moves', '')
                    if moves:
                        # Truncate moves for content to avoid overwhelming
                        moves_snippet = moves[:150] + "..." if len(moves) > 150 else moves
                        content_parts.append(f"Moves: {moves_snippet}")
                    
                    content = " | ".join(content_parts)
                    
                    results.append({
                        'document_id': str(obj.uuid),
                        'content': content,
                        'metadata': {
                            'white_player': white_player,
                            'black_player': black_player,
                            'white_elo': white_elo,
                            'black_elo': black_elo,
                            'event': event,
                            'date': props.get('date_utc', ''),
                            'result': result,
                            'eco': eco,
                            'opening': opening,
                            'ending_fen': props.get('final_fen', ''),
                            'mid_game_fen': props.get('mid_game_fen', ''),
                            'move_count': props.get('ply_count', 0),
                            'source_file': props.get('source_file', ''),
                            'pgn_moves': moves
                        },
                        'weaviate_score': 0.9 - (i * 0.05)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error during Weaviate search for query '{query}': {e}")
            # Fallback: Try direct FEN search if the query contains a FEN
            return self._fallback_fen_search(query, limit)
    
    def _fallback_fen_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Enhanced fallback FEN search that searches positions first, then retrieves games.
        Uses the separate ChessPositions collection to find matching positions,
        then retrieves the corresponding games from ChessGame collection.
        """
        try:
            # Extract FEN from query using the same regex as before
            fen_pattern = r'[rnbqkpRNBQKP1-8/]+\s+[wb]\s+[KQkq-]+\s+[a-h1-8-]+\s+\d+\s+\d+'
            import re
            fen_matches = re.findall(fen_pattern, query)
            
            if not fen_matches:
                logger.info("No FEN pattern found in query for fallback search")
                return []
            
            fen_to_search = fen_matches[0].strip()
            logger.info(f"Attempting fallback FEN search for: {fen_to_search}")
            
            # Import the correct Filter class for v4 syntax
            from weaviate.classes.query import Filter
            
            # Step 1: Search in ChessPositions collection for the FEN
            positions_collection = self.weaviate_client.collections.get("ChessPositions")
            
            # Try multiple search strategies
            all_game_ids = set()
            position_info = {}
            
            # Strategy 1: Search for exact FEN match
            logger.info("Trying exact FEN match")
            position_results = positions_collection.query.fetch_objects(
                filters=Filter.by_property("fen").equal(fen_to_search),
                limit=10,
                return_properties=["fen", "game_ids", "occurrence_count", "white_win_rate", "most_common_eco", "opening_names"]
            )
            
            if position_results and position_results.objects:
                logger.info(f"Found {len(position_results.objects)} exact FEN matches")
                
                for pos_obj in position_results.objects:
                    pos_props = pos_obj.properties
                    game_ids = pos_props.get('game_ids', [])
                    
                    # Collect all game IDs
                    for game_id in game_ids[:20]:  # Limit to first 20 games per position to avoid overload
                        all_game_ids.add(game_id)
                    
                    # Store position information for context
                    position_info[pos_props.get('fen')] = {
                        'occurrence_count': pos_props.get('occurrence_count', 0),
                        'white_win_rate': pos_props.get('white_win_rate', 0.0),
                        'most_common_eco': pos_props.get('most_common_eco', ''),
                        'opening_names': pos_props.get('opening_names', [])
                    }
            
            # Strategy 2: If no exact matches, try FEN without move counters (database format)
            if not all_game_ids:
                logger.info("No exact matches found, trying FEN without move counters")
                fen_parts = fen_to_search.split()
                if len(fen_parts) >= 4:
                    # Remove move counters to match database format: board + color + castling + en_passant
                    fen_without_counters = ' '.join(fen_parts[:4])
                    logger.info(f"Searching for: {fen_without_counters}")
                    
                    position_results = positions_collection.query.fetch_objects(
                        filters=Filter.by_property("fen").equal(fen_without_counters),
                        limit=10,
                        return_properties=["fen", "game_ids", "occurrence_count", "white_win_rate", "most_common_eco", "opening_names"]
                    )
                    
                    if position_results and position_results.objects:
                        logger.info(f"Found {len(position_results.objects)} matches without move counters")
                        for pos_obj in position_results.objects:
                            pos_props = pos_obj.properties
                            game_ids = pos_props.get('game_ids', [])
                            
                            for game_id in game_ids[:15]:  # Slightly fewer for this broader search
                                all_game_ids.add(game_id)
                            
                            position_info[pos_props.get('fen')] = {
                                'occurrence_count': pos_props.get('occurrence_count', 0),
                                'white_win_rate': pos_props.get('white_win_rate', 0.0),
                                'most_common_eco': pos_props.get('most_common_eco', ''),
                                'opening_names': pos_props.get('opening_names', [])
                            }
            
            # Strategy 3: If still no matches, try board position search with LIKE
            if not all_game_ids:
                logger.info("No matches with counters removed, trying board position search")
                fen_parts = fen_to_search.split()
                if fen_parts:
                    board_position = fen_parts[0]
                    logger.info(f"Searching for board position: {board_position}")
                    
                    position_results = positions_collection.query.fetch_objects(
                        filters=Filter.by_property("fen").like(f"{board_position}*"),
                        limit=limit,
                        return_properties=["fen", "game_ids", "occurrence_count", "white_win_rate", "most_common_eco", "opening_names"]
                    )
                    
                    if position_results and position_results.objects:
                        logger.info(f"Found {len(position_results.objects)} board position matches")
                        for pos_obj in position_results.objects:
                            pos_props = pos_obj.properties
                            game_ids = pos_props.get('game_ids', [])
                            
                            for game_id in game_ids[:10]:  # Even fewer for this broadest search
                                all_game_ids.add(game_id)
                            
                            position_info[pos_props.get('fen')] = {
                                'occurrence_count': pos_props.get('occurrence_count', 0),
                                'white_win_rate': pos_props.get('white_win_rate', 0.0),
                                'most_common_eco': pos_props.get('most_common_eco', ''),
                                'opening_names': pos_props.get('opening_names', [])
                            }
            
            if not all_game_ids:
                logger.info("Fallback FEN search found no matching positions")
                return []
            
            # Step 2: Retrieve actual games from ChessGame collection
            games_collection = self.weaviate_client.collections.get("ChessGame")
            
            # Convert game IDs to list and limit
            game_id_list = list(all_game_ids)[:limit]
            logger.info(f"Retrieving {len(game_id_list)} games from position matches")
            
            results = []
            for i, game_id in enumerate(game_id_list):
                try:
                    # Get game by UUID
                    game_result = games_collection.query.fetch_objects(
                        filters=Filter.by_id().equal(game_id),
                        limit=1
                    )
                    
                    if game_result and game_result.objects:
                        game_obj = game_result.objects[0]
                        props = game_obj.properties
                        
                        # Create comprehensive content string that includes ELO data
                        white_player = props.get('white_player', 'Unknown')
                        black_player = props.get('black_player', 'Unknown')
                        white_elo = props.get('white_elo', 'N/A')
                        black_elo = props.get('black_elo', 'N/A')
                        event = props.get('event', '')
                        result = props.get('result', '')
                        eco = props.get('eco', '')
                        opening = props.get('opening', '')
                        
                        content_parts = [
                            f"Game: {white_player} vs {black_player}",
                            f"ELO Ratings: White: {white_elo}, Black: {black_elo}"
                        ]
                        if event:
                            content_parts.append(f"Event: {event}")
                        if result:
                            content_parts.append(f"Result: {result}")
                        if eco:
                            content_parts.append(f"ECO: {eco}")
                        if opening:
                            content_parts.append(f"Opening: {opening}")
                        
                        moves = props.get('pgn_moves', '')
                        if moves:
                            # Truncate moves for content to avoid overwhelming
                            moves_snippet = moves[:150] + "..." if len(moves) > 150 else moves
                            content_parts.append(f"Moves: {moves_snippet}")
                        
                        content = " | ".join(content_parts)
                        
                        # Find the best matching position info for context
                        best_position_info = next(iter(position_info.values())) if position_info else {}
                        
                        results.append({
                            'document_id': str(game_obj.uuid),
                            'content': content,
                            'metadata': {
                                'white_player': white_player,
                                'black_player': black_player,
                                'white_elo': white_elo,
                                'black_elo': black_elo,
                                'event': event,
                                'date': props.get('date_utc', ''),
                                'result': result,
                                'eco': eco,
                                'opening': opening,
                                'ending_fen': props.get('final_fen', ''),
                                'mid_game_fen': props.get('mid_game_fen', ''),
                                'move_count': props.get('ply_count', 0),
                                'source_file': props.get('source_file', ''),
                                'pgn_moves': moves,
                                'fen_match': fen_to_search,
                                'position_occurrence_count': best_position_info.get('occurrence_count', 0),
                                'position_white_win_rate': best_position_info.get('white_win_rate', 0.0),
                                'position_eco': best_position_info.get('most_common_eco', ''),
                                'position_openings': best_position_info.get('opening_names', [])
                            },
                            'weaviate_score': 0.95 - (i * 0.02),  # High score for exact FEN matches
                            'search_type': 'fen_position_lookup'
                        })
                        
                        if len(results) >= limit:
                            break
                            
                except Exception as e:
                    logger.warning(f"Failed to retrieve game {game_id}: {e}")
                    continue
            
            logger.info(f"Fallback FEN search found {len(results)} games")
            return results
            
        except Exception as e:
            logger.error(f"Error during fallback FEN search: {e}")
            return []
    
    def _combine_and_score_results(self, 
                                  semantic_results: List[Dict],
                                  position_results: List[Dict],
                                  tactical_results: List[Dict],
                                  intent_results: List[Dict],
                                  context: ChessContext,
                                  limit: int,
                                  min_relevance: float) -> List[RetrievalResult]:
        """Combine and score all retrieval results"""
        
        # Combine all results
        all_results = {}
        
        # Add semantic results
        for result in semantic_results:
            doc_id = result['document_id']
            all_results[doc_id] = {
                'document_id': doc_id,
                'content': result['content'],
                'semantic_score': result.get('semantic_score', 0.5),
                'position_score': 0.0,
                'tactical_score': 0.0,
                'intent_score': 0.0,
                'metadata': result.get('metadata', {})
            }
        
        # Add position scores
        for result in position_results:
            doc_id = result['document_id']
            if doc_id in all_results:
                all_results[doc_id]['position_score'] = result.get('position_score', 0.0)
            else:
                all_results[doc_id] = {
                    'document_id': doc_id,
                    'content': result['content'],
                    'semantic_score': 0.3,
                    'position_score': result.get('position_score', 0.0),
                    'tactical_score': 0.0,
                    'intent_score': 0.0,
                    'metadata': result.get('metadata', {})
                }
        
        # Add tactical scores
        for result in tactical_results:
            doc_id = result['document_id']
            if doc_id in all_results:
                all_results[doc_id]['tactical_score'] = result.get('tactical_score', 0.0)
            else:
                all_results[doc_id] = {
                    'document_id': doc_id,
                    'content': result['content'],
                    'semantic_score': 0.3,
                    'position_score': 0.0,
                    'tactical_score': result.get('tactical_score', 0.0),
                    'intent_score': 0.0,
                    'metadata': result.get('metadata', {})
                }
        
        # Add intent scores
        for result in intent_results:
            doc_id = result['document_id']
            if doc_id in all_results:
                all_results[doc_id]['intent_score'] = result.get('intent_score', 0.0)
        
        # Calculate final scores using context weights
        weights = self.context_weights.get(context.intent_type, self.context_weights['general'])
        
        final_results = []
        for doc_id, result in all_results.items():
            # Calculate weighted final score
            final_score = (
                result['semantic_score'] * weights['semantic'] +
                result['position_score'] * weights['position'] +
                result['tactical_score'] * weights['tactical']
            )
            
            # Add document type bonus
            doc_type = self._classify_document_type(result['content'])
            if doc_type == context.intent_type:
                final_score += weights['document_type']
            
            # Only include results above threshold
            if final_score >= min_relevance:
                enhanced_result = RetrievalResult(
                    document_id=doc_id,
                    content=result['content'],
                    relevance_score=final_score,
                    context_relevance=final_score,
                    position_relevance=result['position_score'],
                    tactical_relevance=result['tactical_score'],
                    document_type=doc_type,
                    chess_concepts=self._extract_chess_concepts(result['content'])
                )
                final_results.append(enhanced_result)
        
        # Sort by relevance score and return top results
        final_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return final_results[:limit]
    
    def _calculate_position_relevance(self, content: str, fen: str, position_type: str) -> float:
        """Calculate relevance to chess position"""
        content_lower = content.lower()
        score = 0.0
        
        # Position type relevance
        if position_type in content_lower:
            score += 0.3
        
        # Material balance keywords
        if 'material' in content_lower or 'advantage' in content_lower:
            score += 0.2
        
        # Position-specific terms
        position_terms = {
            'opening': ['develop', 'castle', 'center', 'tempo'],
            'middlegame': ['attack', 'defense', 'tactics', 'plan'],
            'endgame': ['technique', 'conversion', 'king', 'pawn']
        }
        
        terms = position_terms.get(position_type, [])
        for term in terms:
            if term in content_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_tactical_relevance(self, content: str, patterns: List[str]) -> float:
        """Calculate relevance to tactical patterns"""
        content_lower = content.lower()
        score = 0.0
        
        for pattern in patterns:
            if pattern in content_lower:
                score += 0.3
        
        # General tactical terms
        tactical_terms = ['tactic', 'combination', 'attack', 'sacrifice', 'puzzle']
        for term in tactical_terms:
            if term in content_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_intent_relevance(self, content: str, intent: str) -> float:
        """Calculate relevance to query intent"""
        content_lower = content.lower()
        
        intent_keywords = {
            'opening': ['opening', 'development', 'principle'],
            'tactics': ['tactical', 'combination', 'puzzle'],
            'strategy': ['strategy', 'plan', 'positional'],
            'endgame': ['endgame', 'technique', 'conversion'],
            'analysis': ['analysis', 'evaluation', 'position']
        }
        
        keywords = intent_keywords.get(intent, [])
        score = sum(0.2 for keyword in keywords if keyword in content_lower)
        
        return min(score, 1.0)
    
    def _classify_document_type(self, content: str) -> str:
        """Classify document type from content"""
        content_lower = content.lower()
        
        for doc_type, keywords in self.document_type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return doc_type
        
        return "general"
    
    def _extract_chess_concepts(self, content: str) -> List[str]:
        """Extract chess concepts from content"""
        content_lower = content.lower()
        concepts = []
        
        # Common chess concepts
        chess_concepts = [
            'development', 'castle', 'center', 'tempo', 'initiative',
            'tactics', 'strategy', 'endgame', 'opening', 'middlegame',
            'attack', 'defense', 'sacrifice', 'combination', 'pin',
            'fork', 'skewer', 'discovery', 'deflection', 'pawn structure'
        ]
        
        for concept in chess_concepts:
            if concept in content_lower:
                concepts.append(concept)
        
        return concepts[:5]  # Limit to top 5 concepts
    
    def _fallback_retrieval(self, query: str, limit: int) -> List[RetrievalResult]:
        """Fallback to base retriever if enhanced retrieval fails"""
        try:
            base_results = self.base_retriever.retrieve_documents(query, limit)
            
            fallback_results = []
            for result in base_results:
                enhanced_result = RetrievalResult(
                    document_id=result.get('id', ''),
                    content=result.get('content', ''),
                    relevance_score=result.get('score', 0.5),
                    context_relevance=0.5,
                    position_relevance=0.0,
                    tactical_relevance=0.0,
                    document_type="general"
                )
                fallback_results.append(enhanced_result)
            
            logger.warning(f"Used fallback retrieval for {len(fallback_results)} documents")
            return fallback_results
            
        except Exception as e:
            logger.error(f"Fallback retrieval also failed: {e}")
            return [] 