"""
Unified Retriever for Chess RAG Application

This module provides a single, consistent retrieval interface that handles all types
of queries using the unified filter system. It replaces the competing retrieval
workflows with a single, well-tested implementation.

Key Features:
- Single retrieval interface for all query types
- Consistent filter application using unified filter system
- Performance optimization through intelligent query routing
- Comprehensive error handling and fallback strategies
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import time

from .unified_filter_system import unified_filter_system, FilterCriteria, FilterPriority

logger = logging.getLogger(__name__)

# Import weaviate client function
try:
    from ..weaviate_loader import get_weaviate_client
except ImportError:
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
    except ImportError:
        # Fallback for direct testing
        def get_weaviate_client():
            import weaviate
            return weaviate.connect_to_local()


@dataclass
class RetrievalResult:
    """Standardized retrieval result"""
    documents: List[Dict[str, Any]]
    total_found: int
    query_type: str
    filters_applied: str
    execution_time: float
    source: str
    metadata: Dict[str, Any]


class UnifiedRetriever:
    """Unified retriever that handles all query types consistently"""
    
    def __init__(self):
        self.logger = logger
        self.filter_system = unified_filter_system
        
        # Collection names
        self.chess_game_collection = "ChessGame"
        self.lesson_collection = "ChessLessonChunk"
        
        # Properties to return for different collection types
        self.game_properties = [
            "white_player", "black_player", "event", "site", "round", "date_utc", 
            "result", "eco", "opening_name", "ply_count", "final_fen", "mid_game_fen",
            "pgn_moves", "source_file", "white_elo", "black_elo", "event_date",
            "white_title", "black_title", "white_fide_id", "black_fide_id", "all_ply_fens"
        ]
        
        self.lesson_properties = [
            "content", "lesson_title", "lesson_number", "diagram_number", 
            "fen", "move_sequence", "concept", "difficulty"
        ]
    
    def retrieve(self, query: str, current_fen: Optional[str] = None, 
                 session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> RetrievalResult:
        """
        Main retrieval method that handles all query types
        
        Args:
            query: User query string
            current_fen: Current board FEN if available
            session_id: Session ID for context
            metadata: Additional metadata from router
            
        Returns:
            RetrievalResult with documents and metadata
        """
        start_time = time.time()
        
        try:
            # Check if router provided filter information
            if metadata and 'filter_request' in metadata:
                # Convert router's GameFilterRequest to FilterCriteria
                criteria = self._convert_game_filter_request_to_criteria(metadata['filter_request'], current_fen)
                self.logger.info(f"Using router's filter request: {metadata['filter_request']}")
            else:
                # Parse query into filter criteria
                criteria = self.filter_system.parse_query_filters(query, current_fen)
            
            # Apply filter prioritization to resolve conflicts
            prioritized_criteria = self.filter_system.apply_filter_prioritization(criteria)
            
            # Determine retrieval strategy based on filter priorities
            strategy = self._determine_retrieval_strategy(prioritized_criteria, query)
            
            # Execute retrieval based on strategy
            documents = self._execute_retrieval_strategy(strategy, prioritized_criteria, query)
            
            # Post-process results
            processed_documents = self._post_process_documents(documents, prioritized_criteria)
            
            execution_time = time.time() - start_time
            
            result = RetrievalResult(
                documents=processed_documents,
                total_found=len(processed_documents),
                query_type=strategy,
                filters_applied=self.filter_system._summarize_criteria(prioritized_criteria),
                execution_time=execution_time,
                source="unified_retriever",
                metadata={
                    "criteria": prioritized_criteria,
                    "original_query": query,
                    "current_fen": current_fen,
                    "session_id": session_id
                }
            )
            
            self.logger.info(f"Retrieved {len(processed_documents)} documents in {execution_time:.3f}s using {strategy} strategy")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Retrieval failed: {e}")
            
            # Return error result
            return RetrievalResult(
                documents=[{"type": "error", "message": f"Retrieval failed: {str(e)}"}],
                total_found=0,
                query_type="error",
                filters_applied="none",
                execution_time=execution_time,
                source="unified_retriever",
                metadata={"error": str(e)}
            )
    
    def _determine_retrieval_strategy(self, criteria: FilterCriteria, query: str) -> str:
        """
        Determine the best retrieval strategy based on filter criteria and query
        
        Args:
            criteria: Parsed and prioritized filter criteria
            query: Original query string
            
        Returns:
            Strategy name
        """
        primary_filter = criteria.get_primary_filter_type()
        
        # Strategy 1: FEN position search (highest priority)
        if primary_filter == FilterPriority.FEN_POSITION:
            return "fen_position_search"
        
        # Strategy 2: Player-based search
        if primary_filter == FilterPriority.PLAYER_NAME:
            return "player_search"
        
        # Strategy 3: ELO filtering (needs advanced filtering)
        if primary_filter == FilterPriority.ELO_RANGE:
            return "advanced_filtering"
        
        # Strategy 4: Opening search
        if primary_filter == FilterPriority.OPENING:
            return "opening_search"
        
        # Strategy 5: Advanced filtering (multiple criteria or any significant filters)
        if criteria.has_high_priority_filters() or len(criteria.priority_filters) > 1:
            return "advanced_filtering"
        
        # Strategy 6: Semantic search (fallback)
        return "semantic_search"
    
    def _execute_retrieval_strategy(self, strategy: str, criteria: FilterCriteria, query: str) -> List[Dict[str, Any]]:
        """
        Execute the determined retrieval strategy
        
        Args:
            strategy: Strategy name
            criteria: Filter criteria
            query: Original query
            
        Returns:
            List of retrieved documents
        """
        if strategy == "fen_position_search":
            return self._fen_position_search(criteria)
        elif strategy == "player_search":
            return self._player_search(criteria)
        elif strategy == "opening_search":
            return self._opening_search(criteria)
        elif strategy == "advanced_filtering":
            return self._advanced_filtering_search(criteria)
        elif strategy == "semantic_search":
            return self._semantic_search(query, criteria)
        else:
            self.logger.warning(f"Unknown strategy: {strategy}, falling back to semantic search")
            return self._semantic_search(query, criteria)
    
    def _fen_position_search(self, criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """
        Search for games containing a specific FEN position
        
        Args:
            criteria: Filter criteria with FEN position
            
        Returns:
            List of games containing the position
        """
        client = get_weaviate_client()
        if not client:
            return [{"type": "error", "message": "Could not connect to Weaviate"}]
        
        try:
            # Use Weaviate v3 syntax instead of v4
            # Build FEN filters using v3 syntax
            where_filter = self._build_v3_fen_filter(criteria)
            
            if not where_filter:
                return [{"type": "error", "message": "Could not build FEN filters"}]
            
            self.logger.info(f"Searching for FEN: {criteria.fen_position}")
            
            # Use v3 query syntax
            response = (client.query
                       .get(self.chess_game_collection, self.game_properties)
                       .with_where(where_filter)
                       .with_limit(criteria.limit)
                       .with_additional(["id"])
                       .do())
            
            # Process v3 response format
            if not (response and response.get("data") and 
                   response["data"].get("Get") and 
                   response["data"]["Get"].get(self.chess_game_collection)):
                return [{"type": "message", "message": f"No games found containing position: {criteria.fen_position}"}]
            
            games = response["data"]["Get"][self.chess_game_collection]
            
            # Convert to standard format
            documents = []
            for game_data in games:
                # Add UUID from additional data
                if "_additional" in game_data and "id" in game_data["_additional"]:
                    game_data["uuid"] = game_data["_additional"]["id"]
                game_data["type"] = "chess_game"
                game_data["source"] = "fen_position_search"
                game_data["matched_fen"] = criteria.fen_position
                documents.append(game_data)
            
            self.logger.info(f"Found {len(documents)} games with FEN position")
            return documents
            
        except Exception as e:
            self.logger.error(f"FEN position search failed: {e}")
            return [{"type": "error", "message": f"FEN search failed: {str(e)}"}]
    
    def _player_search(self, criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """
        Search for games by specific players
        
        Args:
            criteria: Filter criteria with player information
            
        Returns:
            List of games by the specified players
        """
        client = get_weaviate_client()
        if not client:
            return [{"type": "error", "message": "Could not connect to Weaviate"}]
        
        try:
            # Use Weaviate v3 syntax instead of v4
            where_filter = self._build_v3_player_filter(criteria)
            
            if not where_filter:
                return [{"type": "error", "message": "Could not build player filters"}]
            
            player_name = criteria.any_player or criteria.white_player or criteria.black_player
            self.logger.info(f"Searching for games by player: {player_name}")
            
            # Use v3 query syntax
            response = (client.query
                       .get(self.chess_game_collection, self.game_properties)
                       .with_where(where_filter)
                       .with_limit(criteria.limit)
                       .with_additional(["id"])
                       .do())
            
            # Process v3 response format
            if not (response and response.get("data") and 
                   response["data"].get("Get") and 
                   response["data"]["Get"].get(self.chess_game_collection)):
                return [{"type": "message", "message": f"No games found for player: {player_name}"}]
            
            games = response["data"]["Get"][self.chess_game_collection]
            
            # Convert to standard format
            documents = []
            for game_data in games:
                # Add UUID from additional data
                if "_additional" in game_data and "id" in game_data["_additional"]:
                    game_data["uuid"] = game_data["_additional"]["id"]
                game_data["type"] = "chess_game"
                game_data["source"] = "player_search"
                game_data["matched_player"] = player_name
                documents.append(game_data)
            
            self.logger.info(f"Found {len(documents)} games for player: {player_name}")
            return documents
            
        except Exception as e:
            self.logger.error(f"Player search failed: {e}")
            return [{"type": "error", "message": f"Player search failed: {str(e)}"}]
    
    def _opening_search(self, criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """
        Search for games by opening
        
        Args:
            criteria: Filter criteria with opening information
            
        Returns:
            List of games with the specified opening
        """
        client = get_weaviate_client()
        if not client:
            return [{"type": "error", "message": "Could not connect to Weaviate"}]
        
        try:
            collection = client.collections.get(self.chess_game_collection)
            
            # Build opening filters using the unified system
            weaviate_filters = self.filter_system.build_weaviate_filters(criteria)
            
            if not weaviate_filters:
                return [{"type": "error", "message": "Could not build opening filters"}]
            
            opening_name = criteria.opening_name or criteria.eco_code
            self.logger.info(f"Searching for games with opening: {opening_name}")
            
            response = collection.query.fetch_objects(
                filters=weaviate_filters,
                limit=criteria.limit,
                return_properties=self.game_properties
            )
            
            if not response.objects:
                return [{"type": "message", "message": f"No games found with opening: {opening_name}"}]
            
            # Convert to standard format
            documents = []
            for obj in response.objects:
                game_data = obj.properties
                game_data["uuid"] = str(obj.uuid)
                game_data["type"] = "chess_game"
                game_data["source"] = "opening_search"
                game_data["matched_opening"] = opening_name
                documents.append(game_data)
            
            self.logger.info(f"Found {len(documents)} games with opening: {opening_name}")
            return documents
            
        except Exception as e:
            self.logger.error(f"Opening search failed: {e}")
            return [{"type": "error", "message": f"Opening search failed: {str(e)}"}]
    
    def _advanced_filtering_search(self, criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """
        Search using multiple filter criteria
        
        Args:
            criteria: Filter criteria with multiple filters
            
        Returns:
            List of games matching all criteria
        """
        client = get_weaviate_client()
        if not client:
            return [{"type": "error", "message": "Could not connect to Weaviate"}]
        
        try:
            collection = client.collections.get(self.chess_game_collection)
            
            # Build combined filters using the unified system
            weaviate_filters = self.filter_system.build_weaviate_filters(criteria)
            
            if not weaviate_filters:
                return [{"type": "error", "message": "Could not build advanced filters"}]
            
            self.logger.info(f"Searching with advanced filters: {self.filter_system._summarize_criteria(criteria)}")
            
            response = collection.query.fetch_objects(
                filters=weaviate_filters,
                limit=criteria.limit,
                return_properties=self.game_properties
            )
            
            if not response.objects:
                return [{"type": "message", "message": "No games found matching the specified criteria"}]
            
            # Convert to standard format
            documents = []
            for obj in response.objects:
                game_data = obj.properties
                game_data["uuid"] = str(obj.uuid)
                game_data["type"] = "chess_game"
                game_data["source"] = "advanced_filtering"
                game_data["filters_applied"] = self.filter_system._summarize_criteria(criteria)
                documents.append(game_data)
            
            self.logger.info(f"Found {len(documents)} games with advanced filtering")
            return documents
            
        except Exception as e:
            self.logger.error(f"Advanced filtering search failed: {e}")
            return [{"type": "error", "message": f"Advanced filtering failed: {str(e)}"}]
    
    def _semantic_search(self, query: str, criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """
        Perform semantic search as fallback
        
        Args:
            query: Original query string
            criteria: Filter criteria (may be empty)
            
        Returns:
            List of semantically relevant documents
        """
        client = get_weaviate_client()
        if not client:
            return [{"type": "error", "message": "Could not connect to Weaviate"}]
        
        try:
            # Try chess games first
            game_collection = client.collections.get(self.chess_game_collection)
            
            # Build any available filters
            weaviate_filters = self.filter_system.build_weaviate_filters(criteria)
            
            self.logger.info(f"Performing semantic search for: {query}")
            
            # Semantic search on games
            game_response = game_collection.query.near_text(
                query=query,
                filters=weaviate_filters,
                limit=min(criteria.limit // 2, 15),  # Reserve half for lessons
                return_properties=self.game_properties
            )
            
            documents = []
            
            # Add game results
            if game_response.objects:
                for obj in game_response.objects:
                    game_data = obj.properties
                    game_data["uuid"] = str(obj.uuid)
                    game_data["type"] = "chess_game"
                    game_data["source"] = "semantic_search"
                    game_data["relevance_score"] = getattr(obj.metadata, 'distance', 0.0) if hasattr(obj, 'metadata') else 0.0
                    documents.append(game_data)
            
            # Try lesson collection if available
            try:
                lesson_collection = client.collections.get(self.lesson_collection)
                lesson_response = lesson_collection.query.near_text(
                    query=query,
                    limit=min(criteria.limit // 2, 10),
                    return_properties=self.lesson_properties
                )
                
                if lesson_response.objects:
                    for obj in lesson_response.objects:
                        lesson_data = obj.properties
                        lesson_data["uuid"] = str(obj.uuid)
                        lesson_data["type"] = "chess_lesson"
                        lesson_data["source"] = "semantic_search"
                        lesson_data["relevance_score"] = getattr(obj.metadata, 'distance', 0.0) if hasattr(obj, 'metadata') else 0.0
                        documents.append(lesson_data)
                        
            except Exception as lesson_error:
                self.logger.warning(f"Lesson collection not available: {lesson_error}")
            
            if not documents:
                return [{"type": "message", "message": f"No relevant content found for: {query}"}]
            
            self.logger.info(f"Found {len(documents)} documents via semantic search")
            return documents
            
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return [{"type": "error", "message": f"Semantic search failed: {str(e)}"}]
    
    def _post_process_documents(self, documents: List[Dict[str, Any]], criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """
        Post-process retrieved documents to improve quality and relevance.
        Enhanced to handle diagram association quality.
        
        Args:
            documents: Raw retrieved documents
            criteria: Filter criteria used for retrieval
            
        Returns:
            Post-processed and ranked documents
        """
        if not documents:
            return documents
        
        processed_docs = []
        
        for doc in documents:
            # Add document type classification
            # For game documents, use specific fields for classification
            if 'white_player' in doc or 'black_player' in doc or 'pgn_moves' in doc:
                doc_type = 'game'
            else:
                content = doc.get('content', '') or doc.get('text', '') or ''
                if content:
                    doc_type = self._classify_document_type(content)
                else:
                    doc_type = 'general'
            doc['document_type'] = doc_type
            
            # Enhanced diagram quality scoring
            if 'image' in doc or 'diagram_number' in doc:
                diagram_quality_score = self._calculate_diagram_quality_score(doc)
                doc['diagram_quality_score'] = diagram_quality_score
                
                # Filter out low-quality diagram associations if we have better alternatives
                association_confidence = doc.get('association_confidence', 0.0)
                if association_confidence > 0 and association_confidence < 0.3:
                    # Skip very low confidence associations unless no alternatives
                    continue
            
            # Add relevance scoring
            relevance_score = self._calculate_relevance_score(doc, criteria)
            doc['relevance_score'] = relevance_score
            
            processed_docs.append(doc)
        
        # Sort by combined quality and relevance score
        processed_docs.sort(key=lambda x: (
            x.get('diagram_quality_score', 0.0) * 0.4 +  # Diagram quality weight
            x.get('relevance_score', 0.0) * 0.6           # Content relevance weight
        ), reverse=True)
        
        # Limit results and ensure diversity
        final_docs = self._ensure_result_diversity(processed_docs[:25])
        
        return final_docs

    def _calculate_diagram_quality_score(self, doc: Dict[str, Any]) -> float:
        """Calculate quality score for documents with diagrams"""
        base_score = 0.5
        
        # Factor 1: Association confidence
        association_confidence = doc.get('association_confidence', 0.0)
        confidence_score = association_confidence * 0.4
        
        # Factor 2: Match type quality
        match_type = doc.get('match_type', 'unknown')
        match_type_scores = {
            'exact_number': 0.3,
            'explicit_reference': 0.25,
            'close_number': 0.2,
            'proximity': 0.15,
            'semantic': 0.1,
            'fallback': 0.05,
            'unknown': 0.0
        }
        match_score = match_type_scores.get(match_type, 0.0)
        
        # Factor 3: Diagram quality indicator
        diagram_quality = doc.get('diagram_quality', 'unknown')
        quality_scores = {
            'high': 0.2,
            'medium': 0.15,
            'low': 0.1,
            'unknown': 0.05
        }
        quality_score = quality_scores.get(diagram_quality, 0.0)
        
        # Factor 4: Has FEN (indicates successful diagram processing)
        fen_bonus = 0.1 if doc.get('fen') else 0.0
        
        total_score = min(1.0, base_score + confidence_score + match_score + quality_score + fen_bonus)
        return total_score

    def _ensure_result_diversity(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure diversity in results by avoiding too many similar documents"""
        if len(documents) <= 10:
            return documents
        
        diverse_docs = []
        seen_lesson_numbers = set()
        seen_diagram_numbers = set()
        
        # First pass: prioritize high-quality unique content
        for doc in documents:
            lesson_num = doc.get('lesson_number')
            diagram_num = doc.get('diagram_number')
            
            # Always include high-quality diagram matches
            if (doc.get('diagram_quality_score', 0) > 0.8 and 
                diagram_num and diagram_num not in seen_diagram_numbers):
                diverse_docs.append(doc)
                seen_lesson_numbers.add(lesson_num)
                seen_diagram_numbers.add(diagram_num)
                continue
            
            # Include diverse lesson content
            if lesson_num and lesson_num not in seen_lesson_numbers:
                diverse_docs.append(doc)
                seen_lesson_numbers.add(lesson_num)
                if diagram_num:
                    seen_diagram_numbers.add(diagram_num)
            
            # Stop when we have enough diverse content
            if len(diverse_docs) >= 15:
                break
        
        # Second pass: fill remaining slots with best remaining documents
        remaining_slots = 25 - len(diverse_docs)
        for doc in documents:
            if doc not in diverse_docs and remaining_slots > 0:
                diverse_docs.append(doc)
                remaining_slots -= 1
        
        return diverse_docs
    
    def _convert_game_filter_request_to_criteria(self, filter_request, current_fen: Optional[str] = None) -> FilterCriteria:
        """
        Convert router's GameFilterRequest to unified FilterCriteria
        
        Args:
            filter_request: GameFilterRequest from the router
            current_fen: Current board FEN if available
            
        Returns:
            FilterCriteria object
        """
        from .unified_filter_system import FilterCriteria
        
        criteria = FilterCriteria()
        
        # FEN position (highest priority)
        if hasattr(filter_request, 'fen_position') and filter_request.fen_position:
            criteria.fen_position = filter_request.fen_position
            criteria.fen_normalized = self.filter_system._normalize_fen(filter_request.fen_position)
        elif current_fen:
            criteria.fen_position = current_fen
            criteria.fen_normalized = self.filter_system._normalize_fen(current_fen)
        
        # Player filters
        if hasattr(filter_request, 'white_player') and filter_request.white_player:
            criteria.white_player = filter_request.white_player
        if hasattr(filter_request, 'black_player') and filter_request.black_player:
            criteria.black_player = filter_request.black_player
        if hasattr(filter_request, 'any_player') and filter_request.any_player:
            criteria.any_player = filter_request.any_player
        
        # ELO filters - convert EloRange objects to individual min/max values
        if hasattr(filter_request, 'white_elo_range') and filter_request.white_elo_range:
            if hasattr(filter_request.white_elo_range, 'min_elo') and filter_request.white_elo_range.min_elo:
                criteria.white_elo_min = filter_request.white_elo_range.min_elo
            if hasattr(filter_request.white_elo_range, 'max_elo') and filter_request.white_elo_range.max_elo:
                criteria.white_elo_max = filter_request.white_elo_range.max_elo
        
        if hasattr(filter_request, 'black_elo_range') and filter_request.black_elo_range:
            if hasattr(filter_request.black_elo_range, 'min_elo') and filter_request.black_elo_range.min_elo:
                criteria.black_elo_min = filter_request.black_elo_range.min_elo
            if hasattr(filter_request.black_elo_range, 'max_elo') and filter_request.black_elo_range.max_elo:
                criteria.black_elo_max = filter_request.black_elo_range.max_elo
        
        # Opening filters
        if hasattr(filter_request, 'eco_code') and filter_request.eco_code:
            criteria.eco_code = filter_request.eco_code
        if hasattr(filter_request, 'opening_name') and filter_request.opening_name:
            criteria.opening_name = filter_request.opening_name
        
        # Event filters
        if hasattr(filter_request, 'event') and filter_request.event:
            criteria.event = filter_request.event
        if hasattr(filter_request, 'site') and filter_request.site:
            criteria.site = filter_request.site
        
        # Result filters
        if hasattr(filter_request, 'result') and filter_request.result:
            criteria.result = filter_request.result
        
        # Limit
        if hasattr(filter_request, 'limit') and filter_request.limit:
            criteria.limit = filter_request.limit
        else:
            criteria.limit = 25  # Default
        
        self.logger.info(f"Converted GameFilterRequest to FilterCriteria: white_elo_min={criteria.white_elo_min}, black_elo_min={criteria.black_elo_min}")
        return criteria

    def _classify_document_type(self, content: str) -> str:
        """Classify document type from content"""
        content_lower = content.lower()
        
        # Document type keywords
        document_type_keywords = {
            "game": ["pgn", "1.", "white:", "black:", "result:", "event:", "site:", "date:", "round:"],
            "lesson": ["lesson", "chapter", "exercise", "practice", "learn", "study"],
            "analysis": ["analysis", "annotation", "comment", "variation", "line"],
            "opening": ["opening", "debut", "theory", "repertoire", "preparation"],
            "endgame": ["endgame", "ending", "finale", "king and pawn", "rook endgame"],
            "tactics": ["tactic", "puzzle", "combination", "pin", "fork", "skewer", "discovery"],
            "strategy": ["strategy", "plan", "positional", "structure", "weakness", "strength"]
        }
        
        for doc_type, keywords in document_type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return doc_type
        
        return "general"

    def _calculate_relevance_score(self, doc: dict, criteria: any) -> float:
        """Calculate relevance score for a document based on search criteria"""
        score = 0.0
        
        # Base score from Weaviate similarity
        if 'score' in doc:
            score += doc['score']
        elif '_additional' in doc and 'distance' in doc['_additional']:
            # Convert distance to similarity score (lower distance = higher similarity)
            distance = doc['_additional']['distance']
            score += max(0, 1.0 - distance)
        
        # Bonus for document type match
        if hasattr(criteria, 'document_type') and 'document_type' in doc:
            if doc['document_type'] == criteria.document_type:
                score += 0.2
        
        # Bonus for quality scores
        if 'diagram_quality_score' in doc:
            score += doc['diagram_quality_score'] * 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _build_v3_fen_filter(self, criteria: FilterCriteria) -> Optional[Dict[str, Any]]:
        """Build Weaviate v3 filter for FEN position search"""
        if not criteria.fen_position:
            return None
        
        # Build v3 filter for FEN matches
        fen_filters = [
            {
                "path": ["final_fen"],
                "operator": "Equal",
                "valueText": criteria.fen_position
            },
            {
                "path": ["mid_game_fen"],
                "operator": "Equal",
                "valueText": criteria.fen_position
            },
            {
                "path": ["all_ply_fens"],
                "operator": "ContainsAny",
                "valueText": [criteria.fen_position]
            }
        ]
        
        # Add normalized FEN matches if different
        if criteria.fen_normalized and criteria.fen_normalized != criteria.fen_position:
            fen_filters.extend([
                {
                    "path": ["final_fen"],
                    "operator": "Equal",
                    "valueText": criteria.fen_normalized
                },
                {
                    "path": ["mid_game_fen"],
                    "operator": "Equal",
                    "valueText": criteria.fen_normalized
                },
                {
                    "path": ["all_ply_fens"],
                    "operator": "ContainsAny",
                    "valueText": [criteria.fen_normalized]
                }
            ])
        
        return {
            "operator": "Or",
            "operands": fen_filters
        }
    
    def _build_v3_player_filter(self, criteria: FilterCriteria) -> Optional[Dict[str, Any]]:
        """Build Weaviate v3 filter for player search"""
        player_filters = []
        
        if criteria.white_player:
            player_filters.append({
                "path": ["white_player"],
                "operator": "Like",
                "valueText": f"*{criteria.white_player}*"
            })
        
        if criteria.black_player:
            player_filters.append({
                "path": ["black_player"],
                "operator": "Like",
                "valueText": f"*{criteria.black_player}*"
            })
        
        if criteria.any_player:
            any_player_filter = {
                "operator": "Or",
                "operands": [
                    {
                        "path": ["white_player"],
                        "operator": "Like",
                        "valueText": f"*{criteria.any_player}*"
                    },
                    {
                        "path": ["black_player"],
                        "operator": "Like",
                        "valueText": f"*{criteria.any_player}*"
                    }
                ]
            }
            player_filters.append(any_player_filter)
        
        if len(player_filters) > 1:
            return {
                "operator": "And",
                "operands": player_filters
            }
        elif len(player_filters) == 1:
            return player_filters[0]
        else:
            return None


# Global instance
unified_retriever = UnifiedRetriever() 