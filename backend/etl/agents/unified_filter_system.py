"""
Unified Filter System for Chess RAG Application

This module provides a centralized filtering system that handles all types of filters
(FEN, player, ELO, etc.) with proper prioritization and conflict resolution.

Key Features:
- Filter prioritization (FEN > Player > ELO > Other)
- Conflict resolution between filter types
- Consistent filter application across all retrievers
- Performance optimization through filter ordering
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class FilterPriority(Enum):
    """Filter priority levels - higher numbers = higher priority"""
    FEN_POSITION = 100
    PLAYER_NAME = 80
    ELO_RANGE = 60
    OPENING = 50
    EVENT = 40
    DATE_RANGE = 30
    RESULT = 20
    OTHER = 10


@dataclass
class FilterCriteria:
    """Unified filter criteria container"""
    
    # Position filters (highest priority)
    fen_position: Optional[str] = None
    fen_normalized: Optional[str] = None
    
    # Player filters
    white_player: Optional[str] = None
    black_player: Optional[str] = None
    any_player: Optional[str] = None
    
    # ELO filters
    white_elo_min: Optional[int] = None
    white_elo_max: Optional[int] = None
    black_elo_min: Optional[int] = None
    black_elo_max: Optional[int] = None
    
    # Opening filters
    eco_code: Optional[str] = None
    opening_name: Optional[str] = None
    
    # Event filters
    event: Optional[str] = None
    site: Optional[str] = None
    
    # Date filters
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    year: Optional[int] = None
    
    # Result filters
    result: Optional[str] = None
    
    # Metadata
    limit: int = 25
    priority_filters: List[FilterPriority] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate filter priorities after initialization"""
        self.priority_filters = self._calculate_priorities()
    
    def _calculate_priorities(self) -> List[FilterPriority]:
        """Calculate which filters are present and their priorities"""
        priorities = []
        
        if self.fen_position:
            priorities.append(FilterPriority.FEN_POSITION)
        
        if any([self.white_player, self.black_player, self.any_player]):
            priorities.append(FilterPriority.PLAYER_NAME)
        
        if any([self.white_elo_min, self.white_elo_max, self.black_elo_min, self.black_elo_max]):
            priorities.append(FilterPriority.ELO_RANGE)
        
        if any([self.eco_code, self.opening_name]):
            priorities.append(FilterPriority.OPENING)
        
        if any([self.event, self.site]):
            priorities.append(FilterPriority.EVENT)
        
        if any([self.date_from, self.date_to, self.year]):
            priorities.append(FilterPriority.DATE_RANGE)
        
        if self.result:
            priorities.append(FilterPriority.RESULT)
        
        return sorted(priorities, key=lambda x: x.value, reverse=True)
    
    def has_high_priority_filters(self) -> bool:
        """Check if high priority filters (FEN, Player) are present"""
        return any(p.value >= FilterPriority.PLAYER_NAME.value for p in self.priority_filters)
    
    def get_primary_filter_type(self) -> Optional[FilterPriority]:
        """Get the primary (highest priority) filter type"""
        if self.fen_position:
            return FilterPriority.FEN_POSITION
        elif self.any_player or self.white_player or self.black_player:
            return FilterPriority.PLAYER_NAME
        elif self.white_elo_min or self.white_elo_max or self.black_elo_min or self.black_elo_max:
            return FilterPriority.ELO_RANGE
        elif self.eco_code or self.opening_name:
            return FilterPriority.OPENING
        elif self.event or self.site:
            return FilterPriority.EVENT
        elif self.date_from or self.date_to or self.year:
            return FilterPriority.DATE_RANGE
        elif self.result:
            return FilterPriority.RESULT
        else:
            return None


class UnifiedFilterSystem:
    """Unified filter system for consistent filtering across all retrievers"""
    
    def __init__(self):
        self.logger = logger
        
        # FEN regex for validation
        self.fen_regex = re.compile(
            r'([rnbqkpRNBQKP1-8]+/){7}([rnbqkpRNBQKP1-8]+)\s+(w|b)\s+(-|K?Q?k?q?)\s+(-|[a-h][36])\s+(\d+)\s+(\d+)'
        )
        
        # Common player name patterns for better recognition
        self.common_players = {
            'carlsen', 'magnus', 'anand', 'kasparov', 'fischer', 'karpov', 
            'petrosian', 'spassky', 'tal', 'botvinnik', 'capablanca', 'alekhine',
            'nakamura', 'caruana', 'ding', 'nepomniachtchi', 'giri', 'mvl',
            'vachier-lagrave', 'aronian', 'grischuk', 'wesley', 'so'
        }
    
    def parse_query_filters(self, query: str, current_fen: Optional[str] = None) -> FilterCriteria:
        """
        Parse a query and extract all filter criteria with proper prioritization
        
        Args:
            query: User query string
            current_fen: Current board FEN if available
            
        Returns:
            FilterCriteria object with extracted and prioritized filters
        """
        criteria = FilterCriteria()
        query_lower = query.lower().strip()
        
        # Extract FEN from query (highest priority)
        extracted_fen = self._extract_fen_from_query(query)
        if extracted_fen:
            criteria.fen_position = extracted_fen
            criteria.fen_normalized = self._normalize_fen(extracted_fen)
            self.logger.info(f"Extracted FEN from query: {extracted_fen}")
        elif current_fen and self._should_use_current_fen(query):
            criteria.fen_position = current_fen
            criteria.fen_normalized = self._normalize_fen(current_fen)
            self.logger.info(f"Using current FEN: {current_fen}")
        
        # Extract ELO filters BEFORE player filters to prevent conflicts
        self._extract_elo_filters(query_lower, criteria)
        
        # Extract opening filters early (they can help disambiguate)
        self._extract_opening_filters(query_lower, criteria)
        
        # Extract player filters (only if no FEN or explicitly requested, and no ELO filters detected)
        if not criteria.fen_position or self._has_explicit_player_request(query):
            # Skip player extraction if ELO filters were found and no explicit player request
            if not (any([criteria.white_elo_min, criteria.white_elo_max, criteria.black_elo_min, criteria.black_elo_max]) and not self._has_explicit_player_request(query)):
                self._extract_player_filters(query_lower, criteria)
        
        # Extract other filters
        self._extract_event_filters(query_lower, criteria)
        self._extract_date_filters(query_lower, criteria)
        self._extract_result_filters(query_lower, criteria)
        
        # Set limit
        criteria.limit = self._extract_limit(query_lower)
        
        self.logger.info(f"Parsed filters: {self._summarize_criteria(criteria)}")
        return criteria
    
    def apply_filter_prioritization(self, criteria: FilterCriteria) -> FilterCriteria:
        """
        Apply filter prioritization rules to resolve conflicts
        
        Args:
            criteria: Original filter criteria
            
        Returns:
            Prioritized filter criteria with conflicts resolved
        """
        prioritized = FilterCriteria()
        
        # Rule 1: FEN position filters override all others
        if criteria.fen_position:
            prioritized.fen_position = criteria.fen_position
            prioritized.fen_normalized = criteria.fen_normalized
            prioritized.limit = criteria.limit
            
            # Only include ELO and opening filters with FEN (they're compatible)
            prioritized.white_elo_min = criteria.white_elo_min
            prioritized.white_elo_max = criteria.white_elo_max
            prioritized.black_elo_min = criteria.black_elo_min
            prioritized.black_elo_max = criteria.black_elo_max
            prioritized.eco_code = criteria.eco_code
            prioritized.opening_name = criteria.opening_name
            
            self.logger.info("Applied FEN prioritization - removed conflicting player filters")
            return prioritized
        
        # Rule 2: Player filters take precedence over general searches
        if any([criteria.white_player, criteria.black_player, criteria.any_player]):
            prioritized.white_player = criteria.white_player
            prioritized.black_player = criteria.black_player
            prioritized.any_player = criteria.any_player
            
            # Include compatible filters
            prioritized.white_elo_min = criteria.white_elo_min
            prioritized.white_elo_max = criteria.white_elo_max
            prioritized.black_elo_min = criteria.black_elo_min
            prioritized.black_elo_max = criteria.black_elo_max
            prioritized.eco_code = criteria.eco_code
            prioritized.opening_name = criteria.opening_name
            prioritized.event = criteria.event
            prioritized.site = criteria.site
            prioritized.date_from = criteria.date_from
            prioritized.date_to = criteria.date_to
            prioritized.year = criteria.year
            prioritized.result = criteria.result
            prioritized.limit = criteria.limit
            
            self.logger.info("Applied player filter prioritization")
            return prioritized
        
        # Rule 3: No conflicts, return all filters
        return criteria
    
    def build_weaviate_filters(self, criteria: FilterCriteria) -> Optional[Any]:
        """
        Build Weaviate filter objects from criteria
        
        Args:
            criteria: Filter criteria to convert
            
        Returns:
            Weaviate filter object or None if no filters
        """
        try:
            # Try different import paths for weaviate
            try:
                import weaviate.classes.query as weaviate_query
            except ImportError:
                try:
                    from weaviate.collections.classes.filters import Filter as weaviate_query
                except ImportError:
                    self.logger.error("Weaviate not available for filter building")
                    return None
            
            filters = []
            
            # FEN filters (highest priority)
            if criteria.fen_position:
                fen_filters = self._build_fen_filters(criteria, weaviate_query)
                if fen_filters:
                    filters.append(fen_filters)
            
            # Player filters
            player_filters = self._build_player_filters(criteria, weaviate_query)
            if player_filters:
                filters.append(player_filters)
            
            # ELO filters
            elo_filters = self._build_elo_filters(criteria, weaviate_query)
            if elo_filters:
                filters.append(elo_filters)
            
            # Opening filters
            opening_filters = self._build_opening_filters(criteria, weaviate_query)
            if opening_filters:
                filters.append(opening_filters)
            
            # Event filters
            event_filters = self._build_event_filters(criteria, weaviate_query)
            if event_filters:
                filters.append(event_filters)
            
            # Date filters
            date_filters = self._build_date_filters(criteria, weaviate_query)
            if date_filters:
                filters.append(date_filters)
            
            # Result filters
            if criteria.result:
                filters.append(weaviate_query.Filter.by_property("result").equal(criteria.result))
            
            # Combine filters
            if len(filters) > 1:
                return weaviate_query.Filter.all_of(filters)
            elif len(filters) == 1:
                return filters[0]
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error building Weaviate filters: {e}")
            return None
    
    def _extract_fen_from_query(self, query: str) -> Optional[str]:
        """Extract FEN string from query"""
        match = self.fen_regex.search(query)
        return match.group(0) if match else None
    
    def _normalize_fen(self, fen: str) -> str:
        """Normalize FEN for better matching"""
        if not fen:
            return fen
        
        parts = fen.strip().split()
        if len(parts) < 4:
            return fen
        
        # Normalize en passant to '-' for matching
        normalized_parts = parts[:3] + ['-'] + parts[4:]
        return ' '.join(normalized_parts)
    
    def _should_use_current_fen(self, query: str) -> bool:
        """Determine if current FEN should be used for position-based queries"""
        position_keywords = [
            # English keywords
            'position', 'this position', 'current position', 'board',
            'analyze', 'analysis', 'best move', 'evaluation',
            'current fen', 'this fen', 'fen', 'current board',  # Added FEN-specific keywords
            # Russian keywords
            'позиции', 'позицией', 'текущей позиции', 'текущей позицией', 'доска', 'доску',
            'анализ', 'анализируй', 'лучший ход', 'оценка', 'оцени'
        ]
        return any(keyword in query.lower() for keyword in position_keywords)
    
    def _has_explicit_player_request(self, query: str) -> bool:
        """Check if query explicitly requests player information along with FEN"""
        player_keywords = ['player', 'games by', 'who played', 'played by']
        return any(keyword in query.lower() for keyword in player_keywords)
    
    def _extract_player_filters(self, query: str, criteria: FilterCriteria):
        """Extract player name filters"""
        # Skip if we already found an opening
        if criteria.opening_name:
            return
        
        # Skip if query contains FEN-related terms (likely not a player search)
        if any(term in query.lower() for term in ['fen', 'position', 'current board', 'this board']):
            return
        
        # Skip if query contains ELO-related terms (likely not a player search)
        if any(term in query.lower() for term in ['elo', 'rating', 'rated', 'above', 'below', 'higher', 'lower', 'over', 'under']):
            return
            
        # Pattern for "games by [player]" or "[player] games"
        player_patterns = [
            # Specific "find" patterns first (higher priority)
            r'find games (?:for|of|by|with) ([a-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'show me games (?:for|of|by|with) ([a-z\s]+?)(?:\s|$|,|\.|!|\?)',
            # Fixed: Make this pattern more specific to avoid capturing "the current FEN"
            r'search (?:for )?games (?:for|of|by|with) ([a-z]+(?:\s+[a-z]+){0,2})(?:\s+(?:games|matches|vs|against|tournament|championship)|$|,|\.|!|\?)',
            
            # Traditional patterns
            r'games by ([a-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'([a-z\s]+?) vs\s+([a-z\s]+)',
            r'white:\s*([a-z\s]+)',
            r'black:\s*([a-z\s]+)',
            r'player:\s*([a-z\s]+)',
            
            # More specific patterns to avoid false matches
            r'(?:show|get|find) ([a-z\s]+?) games(?:\s|$|,|\.|!|\?)',  # "show Carlsen games"
            r'([a-z\s]+?) games(?:\s|$|,|\.|!|\?)(?!.*(?:find|show|search))',  # "Carlsen games" but not "find Carlsen games"
        ]
        
        for pattern in player_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if len(groups) == 2:  # vs pattern
                    white_player = groups[0].strip()
                    black_player = groups[1].strip()
                    
                    if self._is_likely_player_name(white_player):
                        criteria.white_player = white_player.title()
                    if self._is_likely_player_name(black_player):
                        criteria.black_player = black_player.title()
                        
                elif len(groups) == 1:
                    player_name = groups[0].strip()
                    
                    if self._is_likely_player_name(player_name):
                        # Determine if it should be white, black, or any player
                        if 'white' in query[:match.start()].lower():
                            criteria.white_player = player_name.title()
                        elif 'black' in query[:match.start()].lower():
                            criteria.black_player = player_name.title()
                        else:
                            criteria.any_player = player_name.title()
                        # Break after first successful match to avoid multiple captures
                        break
    
    def _extract_elo_filters(self, query: str, criteria: FilterCriteria):
        """Extract ELO range filters"""
        elo_patterns = [
            # Direct ELO patterns
            r'elo (?:above|over|greater than|higher than|>) (\d+)',
            r'elo (?:below|under|less than|lower than|<) (\d+)',
            r'elo between (\d+) and (\d+)',
            
            # Min/max patterns (NEW)
            r'(?:min|minimum) elo (\d+)',
            r'elo (?:min|minimum) (\d+)',
            r'(?:max|maximum) elo (\d+)',
            r'elo (?:max|maximum) (\d+)',
            
            # Filter/search patterns with ELO
            r'(?:filter|search|find).*?elo (?:above|over|greater than|higher than|>) (\d+)',
            r'(?:filter|search|find).*?elo (?:below|under|less than|lower than|<) (\d+)',
            r'(?:filter|search|find).*?elo between (\d+) and (\d+)',
            
            # Filter/search with min/max patterns (NEW)
            r'(?:filter|search|find).*?(?:min|minimum) elo (\d+)',
            r'(?:filter|search|find).*?elo (?:min|minimum) (\d+)',
            r'(?:filter|search|find).*?(?:max|maximum) elo (\d+)',
            r'(?:filter|search|find).*?elo (?:max|maximum) (\d+)',
            
            # "by min/max" patterns (NEW)
            r'(?:filter|search|find).*?by (?:min|minimum) elo (\d+)',
            r'(?:filter|search|find).*?by (?:max|maximum) elo (\d+)',
            
            # Games/players with ELO patterns
            r'games.*?elo (?:above|over|greater than|higher than|>) (\d+)',
            r'games.*?elo (?:below|under|less than|lower than|<) (\d+)',
            r'games.*?(?:min|minimum) elo (\d+)',  # NEW
            r'games.*?(?:max|maximum) elo (\d+)',  # NEW
            r'players? rated (?:above|over|>) (\d+)',
            r'players? rated (?:below|under|<) (\d+)',
            r'players? rated between (\d+) and (\d+)',
            r'(\d+)\+ rated players?',
            
            # Rating patterns (alternative to ELO)
            r'rating (?:above|over|greater than|higher than|>) (\d+)',
            r'rating (?:below|under|less than|lower than|<) (\d+)',
            r'rating between (\d+) and (\d+)',
            r'(?:min|minimum) rating (\d+)',  # NEW
            r'(?:max|maximum) rating (\d+)',  # NEW
        ]
        
        for pattern in elo_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if len(groups) == 2:  # Range pattern
                    min_elo = int(groups[0])
                    max_elo = int(groups[1])
                    
                    if 'white' in query[:match.start()].lower():
                        criteria.white_elo_min = min_elo
                        criteria.white_elo_max = max_elo
                    elif 'black' in query[:match.start()].lower():
                        criteria.black_elo_min = min_elo
                        criteria.black_elo_max = max_elo
                    else:
                        # Apply to both players
                        criteria.white_elo_min = min_elo
                        criteria.white_elo_max = max_elo
                        criteria.black_elo_min = min_elo
                        criteria.black_elo_max = max_elo
                        
                elif len(groups) == 1:  # Single value pattern
                    elo_value = int(groups[0])
                    
                    # Check if this is a minimum ELO pattern (NEW LOGIC)
                    if ('above' in match.group() or 'over' in match.group() or 'higher' in match.group() or 
                        'greater' in match.group() or '>' in match.group() or 'min' in match.group() or 
                        'minimum' in match.group()):
                        if 'white' in query[:match.start()].lower():
                            criteria.white_elo_min = elo_value
                        elif 'black' in query[:match.start()].lower():
                            criteria.black_elo_min = elo_value
                        else:
                            criteria.white_elo_min = elo_value
                            criteria.black_elo_min = elo_value
                    else:  # below/under/lower/less/max/maximum
                        if 'white' in query[:match.start()].lower():
                            criteria.white_elo_max = elo_value
                        elif 'black' in query[:match.start()].lower():
                            criteria.black_elo_max = elo_value
                        else:
                            criteria.white_elo_max = elo_value
                            criteria.black_elo_max = elo_value
    
    def _extract_opening_filters(self, query: str, criteria: FilterCriteria):
        """Extract opening-related filters"""
        # ECO code pattern
        eco_match = re.search(r'\b([A-E]\d{2})\b', query, re.IGNORECASE)
        if eco_match:
            criteria.eco_code = eco_match.group(1).upper()
        
        # Opening name patterns (check before player extraction)
        opening_patterns = {
            'sicilian': 'Sicilian',
            'sicilian defense': 'Sicilian Defense',
            'ruy lopez': 'Ruy Lopez',
            'spanish': 'Ruy Lopez',
            'french': 'French',
            'french defense': 'French Defense',
            'caro-kann': 'Caro-Kann',
            'caro kann': 'Caro-Kann',
            'queens gambit': "Queen's Gambit",
            'queen\'s gambit': "Queen's Gambit",
            'kings indian': "King's Indian",
            'king\'s indian': "King's Indian",
            'nimzo-indian': 'Nimzo-Indian',
            'nimzo indian': 'Nimzo-Indian',
            'english': 'English',
            'english opening': 'English Opening',
            'catalan': 'Catalan',
            'italian': 'Italian Game',
            'italian game': 'Italian Game',
            'scotch': 'Scotch Game',
            'scotch game': 'Scotch Game',
            'petrov': 'Petrov Defense',
            'petrov defense': 'Petrov Defense',
            'alekhine': 'Alekhine Defense',
            'alekhine defense': 'Alekhine Defense'
        }
        
        query_lower = query.lower()
        for pattern, opening_name in opening_patterns.items():
            if pattern in query_lower:
                criteria.opening_name = opening_name
                break
    
    def _extract_event_filters(self, query: str, criteria: FilterCriteria):
        """Extract event/tournament filters"""
        event_patterns = [
            r'tournament:\s*([^,\n]+)',
            r'event:\s*([^,\n]+)',
            r'in ([^,\n]+?) tournament',
            r'([^,\n]+?) championship',
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                criteria.event = match.group(1).strip()
                break
    
    def _extract_date_filters(self, query: str, criteria: FilterCriteria):
        """Extract date-related filters"""
        # Year pattern
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        if year_match:
            criteria.year = int(year_match.group(0))
        
        # Date range patterns
        date_range_patterns = [
            r'from (\d{4}) to (\d{4})',
            r'between (\d{4}) and (\d{4})',
        ]
        
        for pattern in date_range_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                criteria.date_from = match.group(1)
                criteria.date_to = match.group(2)
                break
    
    def _extract_result_filters(self, query: str, criteria: FilterCriteria):
        """Extract game result filters"""
        if 'white wins' in query or 'white won' in query:
            criteria.result = '1-0'
        elif 'black wins' in query or 'black won' in query:
            criteria.result = '0-1'
        elif 'draw' in query or 'drawn' in query:
            criteria.result = '1/2-1/2'
    
    def _extract_limit(self, query: str) -> int:
        """Extract result limit from query"""
        limit_patterns = [
            r'show (\d+)',
            r'show me (\d+)',
            r'find (\d+)',
            r'top (\d+)',
            r'first (\d+)',
            r'limit (\d+)',
            r'(\d+) games',
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return min(int(match.group(1)), 100)  # Cap at 100
        
        return 25  # Default limit
    
    def _is_likely_player_name(self, name: str) -> bool:
        """Check if a string is likely a player name"""
        if not name or len(name.strip()) < 2:
            return False
        
        name_lower = name.lower().strip()
        
        # Check against common players
        if name_lower in self.common_players:
            return True
        
        # Check for common articles and determiners that are NOT player names
        articles_and_determiners = {
            'the', 'a', 'an', 'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her',
            'our', 'their', 'some', 'any', 'all', 'each', 'every', 'no', 'none'
        }
        
        if name_lower in articles_and_determiners:
            return False
        
        # Check for FEN and chess position terms that are NOT player names
        fen_and_position_terms = {
            'fen', 'current', 'position', 'board', 'analysis', 'move', 'moves',
            'game', 'games', 'match', 'matches', 'tournament', 'championship'
        }
        
        if name_lower in fen_and_position_terms:
            return False
        
        # Check for common chess terms that are NOT player names
        non_player_terms = {
            'games', 'chess', 'position', 'move', 'analysis', 'opening',
            'defense', 'defence', 'attack', 'strategy', 'tactics', 'endgame',
            'tournament', 'match', 'board', 'piece', 'pawn', 'king',
            'queen', 'rook', 'bishop', 'knight', 'castle', 'check',
            'mate', 'draw', 'win', 'lose', 'white', 'black', 'elo',
            'rating', 'fide', 'world', 'championship', 'grand', 'master',
            'sicilian', 'french', 'italian', 'spanish', 'english', 'russian',
            'indian', 'gambit', 'variation', 'line', 'system'
        }
        
        # Add common English action words that are NOT player names
        action_words = {
            'find', 'show', 'get', 'search', 'look', 'see', 'view', 'display',
            'list', 'give', 'tell', 'help', 'play', 'start', 'stop', 'end',
            'make', 'take', 'put', 'set', 'go', 'come', 'run', 'walk',
            'open', 'close', 'save', 'load', 'new', 'old', 'good', 'bad',
            'best', 'worst', 'first', 'last', 'next', 'previous', 'all',
            'some', 'any', 'none', 'many', 'few', 'more', 'less'
        }
        
        if name_lower in non_player_terms or name_lower in action_words:
            return False
        
        # Check for opening-related terms
        opening_terms = {
            'sicilian defense', 'french defense', 'caro-kann', 'kings indian',
            'queens gambit', 'ruy lopez', 'nimzo-indian', 'english opening',
            'italian game', 'scotch game', 'petrov defense', 'alekhine defense'
        }
        
        if name_lower in opening_terms:
            return False
        
        # Basic heuristics for player names
        words = name_lower.split()
        if len(words) > 3:  # Too many words
            return False
        
        # Check if it looks like a name (letters only, proper length)
        if all(word.isalpha() and 2 <= len(word) <= 15 for word in words):
            return True
        
        return False
    
    def _build_fen_filters(self, criteria: FilterCriteria, weaviate_query) -> Optional[Any]:
        """Build FEN-specific Weaviate filters"""
        if not criteria.fen_position:
            return None
        
        fen_filters = []
        
        # Exact FEN matches
        fen_filters.extend([
            weaviate_query.Filter.by_property("final_fen").equal(criteria.fen_position),
            weaviate_query.Filter.by_property("mid_game_fen").equal(criteria.fen_position),
            weaviate_query.Filter.by_property("all_ply_fens").contains_any([criteria.fen_position])
        ])
        
        # Normalized FEN matches if different
        if criteria.fen_normalized and criteria.fen_normalized != criteria.fen_position:
            fen_filters.extend([
                weaviate_query.Filter.by_property("final_fen").equal(criteria.fen_normalized),
                weaviate_query.Filter.by_property("mid_game_fen").equal(criteria.fen_normalized),
                weaviate_query.Filter.by_property("all_ply_fens").contains_any([criteria.fen_normalized])
            ])
        
        return weaviate_query.Filter.any_of(fen_filters)
    
    def _build_player_filters(self, criteria: FilterCriteria, weaviate_query) -> Optional[Any]:
        """Build player-specific Weaviate filters"""
        player_filters = []
        
        if criteria.white_player:
            player_filters.append(
                weaviate_query.Filter.by_property("white_player").like(f"*{criteria.white_player}*")
            )
        
        if criteria.black_player:
            player_filters.append(
                weaviate_query.Filter.by_property("black_player").like(f"*{criteria.black_player}*")
            )
        
        if criteria.any_player:
            any_player_filters = [
                weaviate_query.Filter.by_property("white_player").like(f"*{criteria.any_player}*"),
                weaviate_query.Filter.by_property("black_player").like(f"*{criteria.any_player}*")
            ]
            player_filters.append(weaviate_query.Filter.any_of(any_player_filters))
        
        if len(player_filters) > 1:
            return weaviate_query.Filter.all_of(player_filters)
        elif len(player_filters) == 1:
            return player_filters[0]
        else:
            return None
    
    def _build_elo_filters(self, criteria: FilterCriteria, weaviate_query) -> Optional[Any]:
        """Build ELO-specific Weaviate filters"""
        elo_filters = []
        
        # White ELO filters - use greater_or_equal for inclusive filtering  
        if criteria.white_elo_min:
            elo_filters.append(
                weaviate_query.Filter.by_property("white_elo").greater_or_equal(criteria.white_elo_min)
            )
        if criteria.white_elo_max:
            elo_filters.append(
                weaviate_query.Filter.by_property("white_elo").less_or_equal(criteria.white_elo_max)
            )
        
        # Black ELO filters - use greater_or_equal for inclusive filtering
        if criteria.black_elo_min:
            elo_filters.append(
                weaviate_query.Filter.by_property("black_elo").greater_or_equal(criteria.black_elo_min)
            )
        if criteria.black_elo_max:
            elo_filters.append(
                weaviate_query.Filter.by_property("black_elo").less_or_equal(criteria.black_elo_max)
            )
        
        if len(elo_filters) > 1:
            # Check if we have both white and black minimum ELO filters
            # In this case, use any_of (either player meets the minimum)
            has_white_min = criteria.white_elo_min is not None
            has_black_min = criteria.black_elo_min is not None
            
            if has_white_min and has_black_min and criteria.white_elo_min == criteria.black_elo_min:
                # Same minimum for both players - use any_of (either player meets minimum)
                white_min_filter = weaviate_query.Filter.by_property("white_elo").greater_or_equal(criteria.white_elo_min)
                black_min_filter = weaviate_query.Filter.by_property("black_elo").greater_or_equal(criteria.black_elo_min)
                return weaviate_query.Filter.any_of([white_min_filter, black_min_filter])
            else:
                # Different conditions or mix of min/max - use all_of
                return weaviate_query.Filter.all_of(elo_filters)
        elif len(elo_filters) == 1:
            return elo_filters[0]
        else:
            return None
    
    def _build_opening_filters(self, criteria: FilterCriteria, weaviate_query) -> Optional[Any]:
        """Build opening-specific Weaviate filters"""
        opening_filters = []
        
        if criteria.eco_code:
            opening_filters.append(
                weaviate_query.Filter.by_property("eco").like(f"*{criteria.eco_code}*")
            )
        
        if criteria.opening_name:
            opening_filters.append(
                weaviate_query.Filter.by_property("opening_name").like(f"*{criteria.opening_name}*")
            )
        
        if len(opening_filters) > 1:
            return weaviate_query.Filter.all_of(opening_filters)
        elif len(opening_filters) == 1:
            return opening_filters[0]
        else:
            return None
    
    def _build_event_filters(self, criteria: FilterCriteria, weaviate_query) -> Optional[Any]:
        """Build event-specific Weaviate filters"""
        event_filters = []
        
        if criteria.event:
            event_filters.append(
                weaviate_query.Filter.by_property("event").like(f"*{criteria.event}*")
            )
        
        if criteria.site:
            event_filters.append(
                weaviate_query.Filter.by_property("site").like(f"*{criteria.site}*")
            )
        
        if len(event_filters) > 1:
            return weaviate_query.Filter.all_of(event_filters)
        elif len(event_filters) == 1:
            return event_filters[0]
        else:
            return None
    
    def _build_date_filters(self, criteria: FilterCriteria, weaviate_query) -> Optional[Any]:
        """Build date-specific Weaviate filters"""
        date_filters = []
        
        if criteria.year:
            date_filters.append(
                weaviate_query.Filter.by_property("date_utc").like(f"*{criteria.year}*")
            )
        
        if criteria.date_from and criteria.date_to:
            # This would need more sophisticated date handling
            pass
        
        if len(date_filters) > 1:
            return weaviate_query.Filter.all_of(date_filters)
        elif len(date_filters) == 1:
            return date_filters[0]
        else:
            return None
    
    def _summarize_criteria(self, criteria: FilterCriteria) -> str:
        """Create a summary string of the filter criteria"""
        parts = []
        
        if criteria.fen_position:
            parts.append(f"FEN: {criteria.fen_position[:20]}...")
        
        if criteria.any_player:
            parts.append(f"Player: {criteria.any_player}")
        elif criteria.white_player or criteria.black_player:
            if criteria.white_player:
                parts.append(f"White: {criteria.white_player}")
            if criteria.black_player:
                parts.append(f"Black: {criteria.black_player}")
        
        if criteria.white_elo_min or criteria.black_elo_min:
            parts.append(f"ELO: {criteria.white_elo_min or criteria.black_elo_min}+")
        
        if criteria.eco_code:
            parts.append(f"ECO: {criteria.eco_code}")
        
        if criteria.event:
            parts.append(f"Event: {criteria.event}")
        
        parts.append(f"Limit: {criteria.limit}")
        
        return ", ".join(parts) if parts else "No filters"


# Global instance
unified_filter_system = UnifiedFilterSystem() 