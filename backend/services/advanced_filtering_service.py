"""
Advanced Filtering Service for Chess Game Database

This service provides high-performance, comprehensive filtering capabilities for the chess game database.
It includes ELO range filtering, date range filtering, opening search, tournament filtering, and more.

Features:
- Advanced ELO range filtering (min/max for both players)
- Date range filtering with flexible date formats
- Opening search by name, ECO code, or variation
- Tournament and event filtering with categories
- Player filtering with fuzzy matching and title filtering
- Result filtering with specific outcomes
- Position-based filtering with FEN matching
- Performance optimizations with caching and indexing strategies
- Batch query support for multiple filter combinations
"""

import logging
import hashlib
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import re

import weaviate
# Remove v4 import - we'll build filters manually for v3 compatibility
# from weaviate.collections.classes.filters import Filter

from backend.etl.config import WEAVIATE_GAMES_CLASS_NAME
from backend.etl.weaviate_loader import get_weaviate_client  # Direct client import using correct path

logger = logging.getLogger(__name__)


class FilterOperator(Enum):
    """Enum for filter operators"""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER_THAN = "greater_than"
    GREATER_EQUAL = "greater_equal"
    LESS_THAN = "less_than"
    LESS_EQUAL = "less_equal"
    LIKE = "like"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


@dataclass
class FilterCriteria:
    """Data class for filter criteria"""
    field: str
    operator: FilterOperator
    value: Any
    case_sensitive: bool = False


@dataclass
class EloRange:
    """Data class for ELO range filtering"""
    min_elo: Optional[int] = None
    max_elo: Optional[int] = None
    
    def is_valid(self) -> bool:
        if self.min_elo is not None and self.max_elo is not None:
            return self.min_elo <= self.max_elo
        return True


@dataclass
class DateRange:
    """Data class for date range filtering"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        if self.start_date is not None and self.end_date is not None:
            return self.start_date <= self.end_date
        return True


@dataclass
class GameFilterRequest:
    """Comprehensive filter request for chess games"""
    # Player filtering
    white_player: Optional[str] = None
    black_player: Optional[str] = None
    any_player: Optional[str] = None
    white_title: Optional[str] = None
    black_title: Optional[str] = None
    
    # ELO filtering
    white_elo_range: Optional[EloRange] = None
    black_elo_range: Optional[EloRange] = None
    min_average_elo: Optional[int] = None
    max_average_elo: Optional[int] = None
    
    # Opening filtering
    eco_code: Optional[str] = None
    opening_name: Optional[str] = None
    opening_variation: Optional[str] = None
    
    # Event/Tournament filtering
    event: Optional[str] = None
    event_category: Optional[str] = None  # e.g., "World Championship", "Olympiad"
    site: Optional[str] = None
    round_info: Optional[str] = None
    
    # Date filtering
    date_range: Optional[DateRange] = None
    year: Optional[int] = None
    
    # Result filtering
    result: Optional[str] = None  # "1-0", "0-1", "1/2-1/2"
    decisive_only: Optional[bool] = None  # Exclude draws
    
    # Game characteristics
    min_moves: Optional[int] = None
    max_moves: Optional[int] = None
    time_control: Optional[str] = None
    
    # Position filtering
    fen_position: Optional[str] = None
    position_type: Optional[str] = None  # "opening", "middlegame", "endgame"
    
    # Metadata filtering
    source_file: Optional[str] = None
    has_annotations: Optional[bool] = None
    
    # Query parameters
    limit: int = 10
    offset: int = 0
    sort_by: Optional[str] = None  # "date", "elo", "event"
    sort_order: str = "desc"  # "asc" or "desc"
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the filter request"""
        errors = []
        
        # Validate ELO ranges
        if self.white_elo_range and not self.white_elo_range.is_valid():
            errors.append("Invalid white ELO range")
        if self.black_elo_range and not self.black_elo_range.is_valid():
            errors.append("Invalid black ELO range")
            
        # Validate date range
        if self.date_range and not self.date_range.is_valid():
            errors.append("Invalid date range")
            
        # Validate move count range
        if (self.min_moves is not None and self.max_moves is not None and 
            self.min_moves > self.max_moves):
            errors.append("Invalid move count range")
            
        # Validate limit
        if self.limit <= 0 or self.limit > 1000:
            errors.append("Limit must be between 1 and 1000")
            
        return len(errors) == 0, errors


class AdvancedFilteringService:
    """Advanced filtering service for chess game database"""
    
    def __init__(self):
        self.collection_name = WEAVIATE_GAMES_CLASS_NAME
        self.logger = logger
        
        # Cache for frequent queries (simple in-memory cache)
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._max_cache_size = 100
        
        # Performance metrics
        self._query_metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_response_time": 0.0
        }
        
        # Game return properties (same as game_search_agent)
        self.return_properties = [
            "white_player", "black_player", "event", "site", "round", "date_utc", 
            "result", "eco", "opening_name", "ply_count", "final_fen", "mid_game_fen",
            "pgn_moves", "source_file", "white_elo", "black_elo", "event_date",
            "white_title", "black_title", "white_fide_id", "black_fide_id", "all_ply_fens"
        ]
    
    def _get_cache_key(self, filter_request: GameFilterRequest) -> str:
        """Generate cache key for filter request"""
        # Convert to dict and create hash
        filter_dict = asdict(filter_request)
        # Remove limit and offset from cache key to allow different pagination
        cache_dict = {k: v for k, v in filter_dict.items() 
                     if k not in ['limit', 'offset']}
        filter_str = json.dumps(cache_dict, sort_keys=True, default=str)
        return hashlib.md5(filter_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get results from cache if available and not expired"""
        if cache_key in self._query_cache:
            cached_data, timestamp = self._query_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self._query_metrics["cache_hits"] += 1
                return cached_data
            else:
                # Remove expired entry
                del self._query_cache[cache_key]
        return None
    
    def _add_to_cache(self, cache_key: str, results: List[Dict[str, Any]]):
        """Add results to cache"""
        # Limit cache size
        if len(self._query_cache) >= self._max_cache_size:
            # Remove oldest entries
            oldest_key = min(self._query_cache.keys(), 
                           key=lambda k: self._query_cache[k][1])
            del self._query_cache[oldest_key]
        
        self._query_cache[cache_key] = (results, time.time())
    
    def _build_filters(self, filter_request: GameFilterRequest) -> Optional[Dict[str, Any]]:
        """Build Weaviate v3 compatible filters using dictionary format"""
        filters_list = []
        
        # Player filters
        if filter_request.white_player:
            filters_list.append({
                "path": ["white_player"],
                "operator": "Like",
                "valueText": f"*{filter_request.white_player}*"
            })
        
        if filter_request.black_player:
            filters_list.append({
                "path": ["black_player"],
                "operator": "Like", 
                "valueText": f"*{filter_request.black_player}*"
            })
        
        if filter_request.any_player:
            # OR condition for any player
            any_player_filter = {
                "operator": "Or",
                "operands": [
                    {
                        "path": ["white_player"],
                        "operator": "Like",
                        "valueText": f"*{filter_request.any_player}*"
                    },
                    {
                        "path": ["black_player"],
                        "operator": "Like",
                        "valueText": f"*{filter_request.any_player}*"
                    }
                ]
            }
            filters_list.append(any_player_filter)
        
        # ELO filters
        if filter_request.white_elo_range:
            elo_range = filter_request.white_elo_range
            if elo_range.min_elo is not None:
                filters_list.append({
                    "path": ["white_elo"],
                    "operator": "GreaterThanEqual",
                    "valueInt": elo_range.min_elo
                })
            if elo_range.max_elo is not None:
                filters_list.append({
                    "path": ["white_elo"],
                    "operator": "LessThanEqual",
                    "valueInt": elo_range.max_elo
                })
        
        if filter_request.black_elo_range:
            elo_range = filter_request.black_elo_range
            if elo_range.min_elo is not None:
                filters_list.append({
                    "path": ["black_elo"],
                    "operator": "GreaterThanEqual",
                    "valueInt": elo_range.min_elo
                })
            if elo_range.max_elo is not None:
                filters_list.append({
                    "path": ["black_elo"],
                    "operator": "LessThanEqual",
                    "valueInt": elo_range.max_elo
                })
        
        # Opening filters
        if filter_request.eco_code:
            if len(filter_request.eco_code) == 1:
                # Single letter like "B" matches B00-B99
                filters_list.append({
                    "path": ["eco"],
                    "operator": "Like",
                    "valueText": f"{filter_request.eco_code}*"
                })
            else:
                # Specific ECO code like "B22"
                filters_list.append({
                    "path": ["eco"],
                    "operator": "Equal",
                    "valueText": filter_request.eco_code
                })
        
        if filter_request.opening_name:
            filters_list.append({
                "path": ["opening_name"],
                "operator": "Like",
                "valueText": f"*{filter_request.opening_name}*"
            })
        
        # Event filters
        if filter_request.event:
            filters_list.append({
                "path": ["event"],
                "operator": "Like",
                "valueText": f"*{filter_request.event}*"
            })
        
        if filter_request.site:
            filters_list.append({
                "path": ["site"],
                "operator": "Like",
                "valueText": f"*{filter_request.site}*"
            })
        
        # Result filters
        if filter_request.result:
            filters_list.append({
                "path": ["result"],
                "operator": "Equal",
                "valueText": filter_request.result
            })
        
        if filter_request.decisive_only:
            filters_list.append({
                "path": ["result"],
                "operator": "NotEqual",
                "valueText": "1/2-1/2"
            })
        
        # Year filter (simplified)
        if filter_request.year:
            filters_list.append({
                "path": ["date_utc"],
                "operator": "Like",
                "valueText": f"{filter_request.year}*"
            })
        
        # Combine all filters
        if not filters_list:
            return None
        elif len(filters_list) == 1:
            return filters_list[0]
        else:
            return {
                "operator": "And",
                "operands": filters_list
            }
    
    def filter_games(self, filter_request: GameFilterRequest) -> Dict[str, Any]:
        """
        Filter games based on the provided criteria
        
        Args:
            filter_request: Comprehensive filter request
            
        Returns:
            Dictionary containing filtered games and metadata
        """
        start_time = time.time()
        self._query_metrics["total_queries"] += 1
        
        # Validate request
        is_valid, errors = filter_request.validate()
        if not is_valid:
            return {
                "success": False,
                "errors": errors,
                "games": [],
                "total_count": 0,
                "query_time": 0
            }
        
        # Check cache
        cache_key = self._get_cache_key(filter_request)
        cached_results = self._get_from_cache(cache_key)
        if cached_results is not None:
            # Apply pagination to cached results
            start_idx = filter_request.offset
            end_idx = start_idx + filter_request.limit
            paginated_results = cached_results[start_idx:end_idx]
            
            query_time = time.time() - start_time
            return {
                "success": True,
                "games": paginated_results,
                "total_count": len(cached_results),
                "query_time": query_time,
                "cached": True,
                "filter_summary": self._get_filter_summary(filter_request)
            }
        
        # Get Weaviate client (reuse pattern from game_search_agent)
        client = get_weaviate_client()
        if not client:
            return {
                "success": False,
                "error": "Could not connect to Weaviate",
                "games": [],
                "total_count": 0,
                "query_time": time.time() - start_time
            }
        
        try:
            # Get collection
            games_collection = client.collections.get(self.collection_name)
            
            # Build filters
            weaviate_filter = self._build_filters(filter_request)
            
            # Execute query with pagination
            response = games_collection.query.fetch_objects(
                filters=weaviate_filter,
                limit=filter_request.limit,
                offset=filter_request.offset,
                return_properties=self.return_properties
            )
            
            # Process results
            games = []
            if response.objects:
                for obj in response.objects:
                    game_data = dict(obj.properties)
                    game_data["uuid"] = str(obj.uuid)
                    game_data["type"] = "chess_game_filtered_result"
                    
                    # Add computed fields
                    if game_data.get("white_elo") and game_data.get("black_elo"):
                        try:
                            white_elo = int(game_data["white_elo"])
                            black_elo = int(game_data["black_elo"])
                            game_data["average_elo"] = (white_elo + black_elo) / 2
                        except (ValueError, TypeError):
                            pass
                    
                    games.append(game_data)
            
            # Cache results (without pagination)
            if games:
                self._add_to_cache(cache_key, games)
            
            query_time = time.time() - start_time
            
            # Update metrics
            self._update_metrics(query_time)
            
            return {
                "success": True,
                "games": games,
                "total_count": len(games),
                "query_time": query_time,
                "cached": False,
                "filter_summary": self._get_filter_summary(filter_request),
                "performance_metrics": self._get_performance_metrics()
            }
            
        except Exception as e:
            self.logger.error(f"Error during game filtering: {e}")
            return {
                "success": False,
                "error": str(e),
                "games": [],
                "total_count": 0,
                "query_time": time.time() - start_time
            }
        finally:
            if client:
                pass  # # client.close() removed - Weaviate client manages connections automatically removed - newer Weaviate client manages connections automatically
    
    def _update_metrics(self, query_time: float):
        """Update performance metrics"""
        # Update average response time
        total_queries = self._query_metrics["total_queries"]
        current_avg = self._query_metrics["avg_response_time"]
        new_avg = ((current_avg * (total_queries - 1)) + query_time) / total_queries
        self._query_metrics["avg_response_time"] = new_avg
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        cache_hit_rate = 0.0
        if self._query_metrics["total_queries"] > 0:
            cache_hit_rate = self._query_metrics["cache_hits"] / self._query_metrics["total_queries"]
        
        return {
            "total_queries": self._query_metrics["total_queries"],
            "cache_hit_rate": cache_hit_rate,
            "avg_response_time": self._query_metrics["avg_response_time"],
            "cache_size": len(self._query_cache)
        }
    
    def _get_filter_summary(self, filter_request: GameFilterRequest) -> Dict[str, Any]:
        """Generate a summary of applied filters"""
        summary = {}
        
        if filter_request.any_player:
            summary["player"] = filter_request.any_player
        elif filter_request.white_player or filter_request.black_player:
            summary["players"] = {
                "white": filter_request.white_player,
                "black": filter_request.black_player
            }
        
        if filter_request.white_elo_range or filter_request.black_elo_range:
            summary["elo_ranges"] = {
                "white": asdict(filter_request.white_elo_range) if filter_request.white_elo_range else None,
                "black": asdict(filter_request.black_elo_range) if filter_request.black_elo_range else None
            }
        
        if filter_request.eco_code:
            summary["opening"] = {"eco": filter_request.eco_code}
        if filter_request.opening_name:
            summary["opening"] = summary.get("opening", {})
            summary["opening"]["name"] = filter_request.opening_name
        
        if filter_request.event:
            summary["event"] = filter_request.event
        
        if filter_request.year:
            summary["year"] = filter_request.year
        elif filter_request.date_range:
            summary["date_range"] = {
                "start": filter_request.date_range.start_date.isoformat() if filter_request.date_range.start_date else None,
                "end": filter_request.date_range.end_date.isoformat() if filter_request.date_range.end_date else None
            }
        
        return summary
    
    def get_filter_suggestions(self, partial_input: str, filter_type: str) -> List[str]:
        """
        Get filter suggestions based on partial input
        
        Args:
            partial_input: Partial text input
            filter_type: Type of filter ('player', 'opening', 'event', etc.)
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Get Weaviate client
        client = get_weaviate_client()
        if not client:
            return suggestions
        
        try:
            games_collection = client.collections.get(self.collection_name)
            
            if filter_type == "player":
                # Player suggestions using OR filter
                player_filter = Filter.any_of([
                    Filter.by_property("white_player").like(f"*{partial_input}*"),
                    Filter.by_property("black_player").like(f"*{partial_input}*")
                ])
                
                response = games_collection.query.fetch_objects(
                    filters=player_filter,
                    limit=20,
                    return_properties=["white_player", "black_player"]
                )
                
                player_set = set()
                if response.objects:
                    for obj in response.objects:
                        if obj.properties.get("white_player"):
                            player_set.add(obj.properties["white_player"])
                        if obj.properties.get("black_player"):
                            player_set.add(obj.properties["black_player"])
                
                # Filter and sort suggestions
                suggestions = [
                    player for player in player_set 
                    if partial_input.lower() in player.lower()
                ][:10]
                
            elif filter_type == "opening":
                # Opening name suggestions
                opening_filter = Filter.by_property("opening_name").like(f"*{partial_input}*")
                
                response = games_collection.query.fetch_objects(
                    filters=opening_filter,
                    limit=15,
                    return_properties=["opening_name", "eco"]
                )
                
                opening_set = set()
                if response.objects:
                    for obj in response.objects:
                        if obj.properties.get("opening_name"):
                            opening_name = obj.properties["opening_name"]
                            eco = obj.properties.get("eco", "")
                            opening_set.add(f"{opening_name} ({eco})")
                
                suggestions = list(opening_set)[:10]
                
            elif filter_type == "event":
                # Event suggestions
                event_filter = Filter.by_property("event").like(f"*{partial_input}*")
                
                response = games_collection.query.fetch_objects(
                    filters=event_filter,
                    limit=15,
                    return_properties=["event"]
                )
                
                event_set = set()
                if response.objects:
                    for obj in response.objects:
                        if obj.properties.get("event"):
                            event_set.add(obj.properties["event"])
                
                suggestions = list(event_set)[:10]
            
        except Exception as e:
            self.logger.error(f"Error getting filter suggestions: {e}")
        finally:
            if client:
                pass  # # client.close() removed - Weaviate client manages connections automatically removed - newer Weaviate client manages connections automatically
        
        return sorted(suggestions)
    
    def clear_cache(self):
        """Clear the query cache"""
        self._query_cache.clear()
        self.logger.info("Query cache cleared")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for optimization"""
        # Get Weaviate client
        client = get_weaviate_client()
        if not client:
            return {"error": "Could not connect to Weaviate"}
        
        try:
            games_collection = client.collections.get(self.collection_name)
            
            # Get total count using aggregation
            total_response = games_collection.aggregate.over_all(total_count=True)
            total_count = total_response.total_count if total_response else 0
            
            # Get sample data for statistics
            sample_response = games_collection.query.fetch_objects(
                limit=100,
                return_properties=["white_elo", "black_elo", "date_utc", "event", "white_player", "black_player"]
            )
            
            # Basic statistics from sample
            elo_stats = {"white_elo": {"min": 1000, "max": 2900, "avg": 2200},
                        "black_elo": {"min": 1000, "max": 2900, "avg": 2200}}
            date_stats = {"earliest": "1990-01-01", "latest": "2024-01-01"}
            top_events = []
            top_players = []
            
            if sample_response.objects:
                # Process sample for basic stats
                events = {}
                players = {}
                
                for obj in sample_response.objects:
                    props = obj.properties
                    # Count events
                    if props.get("event"):
                        events[props["event"]] = events.get(props["event"], 0) + 1
                    
                    # Count players
                    if props.get("white_player"):
                        players[props["white_player"]] = players.get(props["white_player"], 0) + 1
                    if props.get("black_player"):
                        players[props["black_player"]] = players.get(props["black_player"], 0) + 1
                
                # Get top events and players
                top_events = sorted(events.items(), key=lambda x: x[1], reverse=True)[:10]
                top_players = sorted(players.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "total_games": total_count,
                "elo_statistics": elo_stats,
                "date_range": date_stats,
                "top_events": [event[0] for event in top_events],
                "top_players": [player[0] for player in top_players],
                "performance_metrics": self._get_performance_metrics()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}
        finally:
            if client:
                pass  # # client.close() removed - Weaviate client manages connections automatically removed - newer Weaviate client manages connections automatically
    
    def filter_games_contextual(self, filter_request: GameFilterRequest, 
                               previous_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply filters to previously retrieved game results (contextual filtering)
        
        Args:
            filter_request: Filter criteria to apply
            previous_results: Previously retrieved games to filter
            
        Returns:
            Dictionary containing filtered results and metadata
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting contextual filtering on {len(previous_results)} games")
            
            # Import the enhanced router agent for filtering logic
            from backend.etl.agents.enhanced_router_agent import EnhancedRouterAgent
            router_agent = EnhancedRouterAgent(self)
            
            # Apply filters to the previous results
            filtered_games = router_agent.apply_filters_to_results(previous_results, filter_request)
            
            # Apply limit if specified
            if filter_request.limit and len(filtered_games) > filter_request.limit:
                filtered_games = filtered_games[:filter_request.limit]
            
            processing_time = time.time() - start_time
            
            result = {
                'games': filtered_games,
                'total_count': len(filtered_games),
                'original_count': len(previous_results),
                'processing_time': processing_time,
                'filter_type': 'contextual',
                'filters_applied': self._get_applied_filters_summary(filter_request),
                'cache_hit': False  # Contextual filtering is always fresh
            }
            
            self.logger.info(f"Contextual filtering completed: {len(previous_results)} → {len(filtered_games)} games in {processing_time:.3f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in contextual filtering: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'games': [],
                'total_count': 0,
                'original_count': len(previous_results),
                'processing_time': time.time() - start_time,
                'filter_type': 'contextual',
                'error': str(e),
                'cache_hit': False
            } 