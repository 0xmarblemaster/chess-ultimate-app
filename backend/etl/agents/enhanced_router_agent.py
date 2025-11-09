"""
Enhanced Router Agent for Advanced Filtering

This enhanced router agent can parse natural language queries and extract structured
filtering criteria for the advanced filtering service. It uses NLP techniques to
identify player names, ELO ranges, dates, openings, and other filter criteria
from user queries.

Features:
- Natural language parsing for filter extraction
- ELO range detection (e.g., "players rated above 2600")
- Date range parsing (e.g., "games from 2020 to 2023")
- Player name extraction with fuzzy matching
- Opening name and ECO code detection
- Tournament and event filtering
- Result and game characteristic filtering
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import calendar

from backend.services.advanced_filtering_service import (
    GameFilterRequest, EloRange, DateRange, AdvancedFilteringService
)

logger = logging.getLogger(__name__)


class EnhancedRouterAgent:
    """Enhanced router agent for parsing filtering queries"""
    
    def __init__(self, filtering_service: Optional[AdvancedFilteringService] = None):
        self.filtering_service = filtering_service or AdvancedFilteringService()
        self.logger = logger
        
        # Common chess player names for better recognition
        self.common_players = {
            'carlsen', 'magnus', 'anand', 'kasparov', 'fischer', 'karpov', 
            'petrosian', 'spassky', 'tal', 'botvinnik', 'capablanca', 'alekhine',
            'nakamura', 'caruana', 'ding', 'nepomniachtchi', 'giri', 'mvl',
            'vachier-lagrave', 'aronian', 'grischuk', 'wesley', 'so'
        }
        
        # Multilingual keyword patterns for query classification
        self.language_patterns = {
            'game_search': {
                'en': ['games', 'search', 'find', 'show me', 'player', 'match', 'contest'],
                'ru': ['партии', 'партию', 'игры', 'игру', 'найди', 'найти', 'покажи', 'поиск', 'игрок', 'матч']
            },
            'opening_lookup': {
                'en': ['opening', 'defense', 'gambit', 'variation', 'eco'],
                'ru': ['дебют', 'защита', 'гамбит', 'вариант', 'эко', 'начало']
            },
            'position_analysis': {
                'en': ['analyze', 'analysis', 'best move', 'evaluation', 'stockfish', 'engine'],
                'ru': ['анализ', 'анализируй', 'лучший ход', 'оценка', 'стокфиш', 'движок']
            },
            'move_history': {
                'en': ['moves', 'history', 'pgn', 'game so far'],
                'ru': ['ходы', 'история', 'пгн', 'партия до сих пор']
            },
            'position_related': {
                'en': ['position', 'current position', 'this position', 'for position'],
                'ru': ['позиция', 'позиции', 'текущей позиции', 'для позиции', 'эта позиция', 'данной позиции']
            }
        }
        
        # Common opening names and ECO codes
        self.opening_patterns = {
            'sicilian': ['B20', 'B21', 'B22', 'B30', 'B40', 'B50', 'B60', 'B70', 'B80', 'B90'],
            'ruy lopez': ['C60', 'C70', 'C80', 'C90'],
            'french': ['C00', 'C10', 'C20'],
            'caro-kann': ['B10', 'B12', 'B15'],
            'queens gambit': ['D06', 'D30', 'D31', 'D37'],
            'kings indian': ['E60', 'E70', 'E80', 'E90'],
            'nimzo-indian': ['E20', 'E30', 'E40', 'E50'],
            'english': ['A10', 'A20', 'A30'],
            'catalan': ['E00', 'E01', 'E02', 'E03']
        }
        
        # Tournament and event patterns
        self.tournament_patterns = {
            'world championship': ['World Championship', 'WCC', 'World Ch'],
            'candidates': ['Candidates', 'Candidate'],
            'olympiad': ['Olympiad', 'Chess Olympiad'],
            'grand prix': ['Grand Prix', 'GP'],
            'super tournament': ['Wijk aan Zee', 'Linares', 'Dortmund', 'Norway Chess'],
            'rapid': ['Rapid', 'Blitz', 'Speed'],
            'classical': ['Classical', 'Standard']
        }
    
    def parse_filter_query(self, query: str) -> GameFilterRequest:
        """
        Parse a natural language query and extract filter criteria
        
        Args:
            query: Natural language query string
            
        Returns:
            GameFilterRequest object with extracted criteria
        """
        query_lower = query.lower().strip()
        
        # Initialize filter request
        filter_request = GameFilterRequest()
        
        # Extract different types of filters (use lowercase for text-based filters)
        self._extract_player_filters(query_lower, filter_request)
        self._extract_elo_filters(query_lower, filter_request)
        self._extract_date_filters(query_lower, filter_request)
        self._extract_opening_filters(query_lower, filter_request)
        self._extract_event_filters(query_lower, filter_request)
        self._extract_result_filters(query_lower, filter_request)
        self._extract_game_characteristic_filters(query_lower, filter_request)
        
        # CRITICAL FIX: Use original query for position filters to preserve FEN case
        self._extract_position_filters(query.strip(), filter_request)
        
        # Set default limit if not specified
        if not self._has_limit_in_query(query_lower):
            filter_request.limit = 10
        
        self.logger.info(f"Parsed query '{query}' into filter request: {self._summarize_filters(filter_request)}")
        
        return filter_request
    
    def _extract_player_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract player-related filters from query"""
        
        # Pattern for "games by [player]" or "[player] games" in English and Russian
        player_patterns = [
            # English patterns
            r'games by ([a-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'([a-z\s]+?) games',
            r'([a-z\s]+?) vs\s+([a-z\s]+)',
            r'white:\s*([a-z\s]+)',
            r'black:\s*([a-z\s]+)',
            r'player:\s*([a-z\s]+)',
            r'show me games of ([a-z\s]+)',
            r'find games with ([a-z\s]+)',
            
            # Russian patterns
            r'партии ([а-яёa-z\s]+?)(?:\s|$|,|\.|!|\?)',  # "партии [игрок]"
            r'найди партии ([а-яёa-z\s]+?)(?:\s|$|,|\.|!|\?)',  # "найди партии [игрок]"
            r'найти партии ([а-яёa-z\s]+?)(?:\s|$|,|\.|!|\?)',  # "найти партии [игрок]" 
            r'игры ([а-яёa-z\s]+?)(?:\s|$|,|\.|!|\?)',  # "игры [игрок]"
            r'([а-яёa-z\s]+?) против\s+([а-яёa-z\s]+)',  # "[игрок1] против [игрок2]"
            r'белые:\s*([а-яёa-z\s]+)',  # "белые: [игрок]"
            r'чёрные:\s*([а-яёa-z\s]+)',  # "чёрные: [игрок]"
            r'игрок:\s*([а-яёa-z\s]+)',  # "игрок: [игрок]"
            r'покажи игры ([а-яёa-z\s]+?)(?:\s|$|,|\.|!|\?)',  # "покажи игры [игрок]"
            r'найди игры с ([а-яёa-z\s]+?)(?:\s|$|,|\.|!|\?)',  # "найди игры с [игрок]"
        ]
        
        for pattern in player_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if len(groups) == 2:  # vs pattern
                    white_player = groups[0].strip()
                    black_player = groups[1].strip()
                    
                    if self._is_likely_player_name(white_player):
                        filter_request.white_player = white_player.title()
                    if self._is_likely_player_name(black_player):
                        filter_request.black_player = black_player.title()
                        
                elif len(groups) == 1:
                    player_name = groups[0].strip()
                    
                    if self._is_likely_player_name(player_name):
                        # Determine if it should be white, black, or any player
                        if 'white' in query[:match.start()].lower():
                            filter_request.white_player = player_name.title()
                        elif 'black' in query[:match.start()].lower():
                            filter_request.black_player = player_name.title()
                        else:
                            filter_request.any_player = player_name.title()
        
        # Look for title filters
        if 'grandmaster' in query or ' gm ' in query:
            filter_request.white_title = 'GM'
            filter_request.black_title = 'GM'
        elif 'international master' in query or ' im ' in query:
            filter_request.white_title = 'IM'
            filter_request.black_title = 'IM'
    
    def _extract_elo_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract ELO-related filters from query"""
        
        # Pattern for ELO ranges in English and Russian
        elo_patterns = [
            # English patterns
            r'elo (?:above|over|greater than|>) (\d+)',
            r'elo (?:below|under|less than|<) (\d+)',
            r'elo between (\d+) and (\d+)',
            r'elo from (\d+) to (\d+)',
            
            # Min/max patterns (English)
            r'(?:min|minimum) elo (\d+)',
            r'elo (?:min|minimum) (\d+)',
            r'(?:max|maximum) elo (\d+)',
            r'elo (?:max|maximum) (\d+)',
            
            # Filter/search with min/max patterns (English)
            r'(?:filter|search|find).*?(?:min|minimum) elo (\d+)',
            r'(?:filter|search|find).*?elo (?:min|minimum) (\d+)',
            r'(?:filter|search|find).*?(?:max|maximum) elo (\d+)',
            r'(?:filter|search|find).*?elo (?:max|maximum) (\d+)',
            
            # "by min/max" patterns (English)
            r'(?:filter|search|find).*?by (?:min|minimum) elo (\d+)',
            r'(?:filter|search|find).*?by (?:max|maximum) elo (\d+)',
            
            # Russian patterns
            r'эло (?:выше|больше|свыше) (\d+)',  # "эло выше [число]"
            r'эло (?:ниже|меньше) (\d+)',  # "эло ниже [число]"
            r'эло между (\d+) и (\d+)',  # "эло между [число] и [число]"
            r'эло от (\d+) до (\d+)',  # "эло от [число] до [число]"
            r'(?:мин|минимум) эло (\d+)',  # "мин эло [число]"
            r'эло (?:мин|минимум) (\d+)',  # "эло мин [число]"
            r'(?:макс|максимум) эло (\d+)',  # "макс эло [число]"
            r'эло (?:макс|максимум) (\d+)',  # "эло макс [число]"
            r'рейтинг(?:ом|е|а)?\s*(?:выше|больше|свыше) (\d+)',  # "рейтинг выше [число]" with case variations
            r'рейтинг(?:ом|е|а)?\s*(?:ниже|меньше) (\d+)',  # "рейтинг ниже [число]" with case variations
            r'с рейтингом (?:выше|больше|свыше) (\d+)',  # "с рейтингом выше [число]"
            r'с рейтингом (?:ниже|меньше) (\d+)',  # "с рейтингом ниже [число]"
            
            r'players? rated (?:above|over|>) (\d+)',
            r'players? rated (?:below|under|<) (\d+)',
            r'players? rated between (\d+) and (\d+)',
            r'rating (?:above|over|>) (\d+)',
            r'rating (?:below|under|<) (\d+)',
            r'(?:min|minimum) rating (\d+)',  # NEW
            r'(?:max|maximum) rating (\d+)',  # NEW
            r'(\d+)\+ rated players?',
            r'(\d+)\+ elo',
        ]
        
        for pattern in elo_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if len(groups) == 2:  # Range pattern
                    min_elo = int(groups[0])
                    max_elo = int(groups[1])
                    
                    # Determine if it's for white, black, or both
                    if 'white' in query[:match.start()].lower():
                        filter_request.white_elo_range = EloRange(min_elo, max_elo)
                    elif 'black' in query[:match.start()].lower():
                        filter_request.black_elo_range = EloRange(min_elo, max_elo)
                    else:
                        # Apply to both players
                        filter_request.white_elo_range = EloRange(min_elo, max_elo)
                        filter_request.black_elo_range = EloRange(min_elo, max_elo)
                        
                elif len(groups) == 1:  # Single value pattern
                    elo_value = int(groups[0])
                    
                    # Check if this is a minimum ELO pattern (UPDATED LOGIC)
                    matched_text = match.group().lower()
                    if ('above' in matched_text or 'over' in matched_text or '>' in matched_text or
                        'min' in matched_text or 'minimum' in matched_text or
                        'выше' in matched_text or 'больше' in matched_text or 'свыше' in matched_text or
                        'мин' in matched_text or 'минимум' in matched_text):
                        # Minimum ELO
                        if 'white' in query[:match.start()].lower():
                            filter_request.white_elo_range = EloRange(min_elo=elo_value)
                        elif 'black' in query[:match.start()].lower():
                            filter_request.black_elo_range = EloRange(min_elo=elo_value)
                        else:
                            filter_request.white_elo_range = EloRange(min_elo=elo_value)
                            filter_request.black_elo_range = EloRange(min_elo=elo_value)
                            
                    elif ('below' in matched_text or 'under' in matched_text or '<' in matched_text or
                          'max' in matched_text or 'maximum' in matched_text or
                          'ниже' in matched_text or 'меньше' in matched_text or
                          'макс' in matched_text or 'максимум' in matched_text):
                        # Maximum ELO
                        if 'white' in query[:match.start()].lower():
                            filter_request.white_elo_range = EloRange(max_elo=elo_value)
                        elif 'black' in query[:match.start()].lower():
                            filter_request.black_elo_range = EloRange(max_elo=elo_value)
                        else:
                            filter_request.white_elo_range = EloRange(max_elo=elo_value)
                            filter_request.black_elo_range = EloRange(max_elo=elo_value)
        
        # Pattern for average ELO
        avg_elo_patterns = [
            r'average elo (?:above|over|>) (\d+)',
            r'average elo (?:below|under|<) (\d+)',
            r'average rating (?:above|over|>) (\d+)',
            r'average rating (?:below|under|<) (\d+)',
        ]
        
        for pattern in avg_elo_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                elo_value = int(match.groups()[0])
                
                if 'above' in match.group() or 'over' in match.group() or '>' in match.group():
                    filter_request.min_average_elo = elo_value
                elif 'below' in match.group() or 'under' in match.group() or '<' in match.group():
                    filter_request.max_average_elo = elo_value
    
    def _extract_date_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract date-related filters from query"""
        
        # Year patterns
        year_patterns = [
            r'in (\d{4})',
            r'from (\d{4})',
            r'year (\d{4})',
            r'(\d{4}) games',
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, query)
            if match:
                year = int(match.groups()[0])
                if 1900 <= year <= 2030:  # Reasonable year range
                    filter_request.year = year
                break
        
        # Date range patterns
        date_range_patterns = [
            r'from (\d{4}) to (\d{4})',
            r'between (\d{4}) and (\d{4})',
            r'(\d{4})-(\d{4})',
        ]
        
        for pattern in date_range_patterns:
            match = re.search(pattern, query)
            if match:
                start_year = int(match.groups()[0])
                end_year = int(match.groups()[1])
                
                if 1900 <= start_year <= end_year <= 2030:
                    start_date = datetime(start_year, 1, 1)
                    end_date = datetime(end_year, 12, 31, 23, 59, 59)
                    filter_request.date_range = DateRange(start_date, end_date)
                break
        
        # Recent/last patterns
        recent_patterns = [
            r'last (\d+) years?',
            r'recent (\d+) years?',
            r'past (\d+) years?',
        ]
        
        for pattern in recent_patterns:
            match = re.search(pattern, query)
            if match:
                years_back = int(match.groups()[0])
                end_date = datetime.now()
                start_date = datetime(end_date.year - years_back, 1, 1)
                filter_request.date_range = DateRange(start_date, end_date)
                break
    
    def _extract_opening_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract opening-related filters from query"""
        
        # Check for direct ECO codes
        eco_pattern = r'\b([A-E](?:\d{2})?)\b'
        eco_matches = re.finditer(eco_pattern, query, re.IGNORECASE)
        for match in eco_matches:
            eco_code = match.groups()[0].upper()
            filter_request.eco_code = eco_code
            break
        
        # Check for opening names
        for opening_name, eco_codes in self.opening_patterns.items():
            if opening_name in query:
                filter_request.opening_name = opening_name.title()
                if not filter_request.eco_code and eco_codes:
                    # Use the first ECO code as a default
                    filter_request.eco_code = eco_codes[0][0]  # First letter only for broad match
                break
        
        # Generic opening pattern
        opening_patterns = [
            r'opening:\s*([a-z\s\-\']+)',
            r'([a-z\s\-\']+) opening',
            r'([a-z\s\-\']+) defense',
            r'([a-z\s\-\']+) variation',
        ]
        
        for pattern in opening_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                opening_name = match.groups()[0].strip()
                if len(opening_name) > 3:  # Avoid very short matches
                    filter_request.opening_name = opening_name.title()
                break
    
    def _extract_event_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract event/tournament-related filters from query"""
        
        # Check for known tournament patterns
        for tournament_type, tournament_names in self.tournament_patterns.items():
            for tournament_name in tournament_names:
                if tournament_name.lower() in query:
                    filter_request.event = tournament_name
                    filter_request.event_category = tournament_type
                    return
        
        # Generic event patterns
        event_patterns = [
            r'tournament:\s*([a-z\s\-\']+)',
            r'event:\s*([a-z\s\-\']+)',
            r'in ([a-z\s\-\']+) tournament',
            r'([a-z\s\-\']+) championship',
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                event_name = match.groups()[0].strip()
                if len(event_name) > 3:
                    filter_request.event = event_name.title()
                break
        
        # Location/site filters
        site_patterns = [
            r'in ([a-z\s\-\']+)(?:\s|$|,)',
            r'at ([a-z\s\-\']+)(?:\s|$|,)',
            r'site:\s*([a-z\s\-\']+)',
        ]
        
        for pattern in site_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                site_name = match.groups()[0].strip()
                if len(site_name) > 2 and site_name not in ['the', 'and', 'or']:
                    filter_request.site = site_name.title()
                break
    
    def _extract_result_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract result-related filters from query"""
        
        # Specific results
        if 'white wins' in query or 'white won' in query or '1-0' in query:
            filter_request.result = '1-0'
        elif 'black wins' in query or 'black won' in query or '0-1' in query:
            filter_request.result = '0-1'
        elif 'draw' in query or 'drawn' in query or '1/2-1/2' in query:
            filter_request.result = '1/2-1/2'
        elif 'decisive' in query or 'no draws' in query:
            filter_request.decisive_only = True
    
    def _extract_game_characteristic_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract game characteristic filters from query"""
        
        # Move count patterns
        move_patterns = [
            r'(?:more than|over|>) (\d+) moves?',
            r'(?:less than|under|<) (\d+) moves?',
            r'between (\d+) and (\d+) moves?',
            r'(\d+)\+ moves?',
            r'short games?',  # Less than 30 moves
            r'long games?',   # More than 60 moves
        ]
        
        for pattern in move_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if 'short' in pattern:
                    filter_request.max_moves = 30
                elif 'long' in pattern:
                    filter_request.min_moves = 60
                elif match.groups():
                    groups = match.groups()
                    if len(groups) == 2:  # Range
                        filter_request.min_moves = int(groups[0])
                        filter_request.max_moves = int(groups[1])
                    elif len(groups) == 1:  # Single value
                        move_count = int(groups[0])
                        if 'more' in match.group() or 'over' in match.group() or '+' in match.group():
                            filter_request.min_moves = move_count
                        elif 'less' in match.group() or 'under' in match.group():
                            filter_request.max_moves = move_count
                break
        
        # Time control patterns
        if 'rapid' in query:
            filter_request.time_control = 'rapid'
        elif 'blitz' in query:
            filter_request.time_control = 'blitz'
        elif 'classical' in query or 'standard' in query:
            filter_request.time_control = 'classical'
    
    def _extract_position_filters(self, query: str, filter_request: GameFilterRequest):
        """Extract position-related filters from query"""
        
        # Look for FEN strings - PRESERVE ORIGINAL CASE for FEN extraction
        # FEN format: piece_placement active_color castling en_passant halfmove_clock fullmove_number
        # Example: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
        fen_pattern = r'([rnbqkpRNBQKP1-8/]+\s+[wb]\s+[KQkq-]+\s+[a-h1-8-]+\s+\d+\s+\d+)'
        fen_match = re.search(fen_pattern, query)
        if fen_match:
            # CRITICAL FIX: Preserve the original case from the match
            original_fen = fen_match.group(1)
            filter_request.fen_position = original_fen
            self.logger.info(f"Extracted FEN with preserved case: '{original_fen}'")
        
        # Position type keywords (use case-insensitive for these)
        query_lower = query.lower()
        if 'opening' in query_lower:
            filter_request.position_type = 'opening'
        elif 'middlegame' in query_lower or 'middle game' in query_lower:
            filter_request.position_type = 'middlegame'
        elif 'endgame' in query_lower or 'end game' in query_lower:
            filter_request.position_type = 'endgame'
    
    def _is_likely_player_name(self, name: str) -> bool:
        """Determine if a string is likely a player name"""
        name_lower = name.lower()
        
        # Check against known players
        if name_lower in self.common_players:
            return True
        
        # CRITICAL FIX: Exclude common query words that are not player names
        query_words = {
            'find', 'show', 'get', 'search', 'look', 'display', 'tell', 'give', 'list',
            'games', 'game', 'matches', 'match', 'results', 'result', 'position', 'positions',
            'this', 'that', 'these', 'those', 'for', 'with', 'from', 'to', 'by', 'in', 'at', 'on',
            'the', 'and', 'or', 'but', 'if', 'when', 'where', 'how', 'what', 'who', 'why',
            'chess', 'opening', 'defense', 'gambit', 'variation', 'line', 'theory',
            'analyze', 'analysis', 'evaluate', 'evaluation', 'study', 'learn'
        }
        
        if name_lower in query_words:
            return False
        
        # Check if it looks like a surname (common chess convention)
        if len(name.split()) <= 2 and len(name) > 2:
            # Avoid common non-name words
            non_names = {'the', 'and', 'or', 'in', 'at', 'on', 'by', 'with', 'from', 'to', 'game', 'games', 'chess', 'opening', 'defense'}
            if name_lower not in non_names:
                return True
        
        return False
    
    def _has_limit_in_query(self, query: str) -> bool:
        """Check if query specifies a limit"""
        limit_patterns = [
            r'show (\d+)',
            r'find (\d+)',
            r'get (\d+)',
            r'(\d+) games?',
            r'top (\d+)',
            r'first (\d+)',
        ]
        
        for pattern in limit_patterns:
            if re.search(pattern, query):
                return True
        return False
    
    def _summarize_filters(self, filter_request: GameFilterRequest) -> str:
        """Create a summary of the extracted filters"""
        summary_parts = []
        
        if filter_request.any_player:
            summary_parts.append(f"player: {filter_request.any_player}")
        elif filter_request.white_player or filter_request.black_player:
            if filter_request.white_player:
                summary_parts.append(f"white: {filter_request.white_player}")
            if filter_request.black_player:
                summary_parts.append(f"black: {filter_request.black_player}")
        
        if filter_request.white_elo_range or filter_request.black_elo_range:
            if filter_request.white_elo_range:
                elo_range = filter_request.white_elo_range
                if elo_range.min_elo and elo_range.max_elo:
                    summary_parts.append(f"white ELO: {elo_range.min_elo}-{elo_range.max_elo}")
                elif elo_range.min_elo:
                    summary_parts.append(f"white ELO: >{elo_range.min_elo}")
                elif elo_range.max_elo:
                    summary_parts.append(f"white ELO: <{elo_range.max_elo}")
        
        if filter_request.eco_code:
            summary_parts.append(f"ECO: {filter_request.eco_code}")
        if filter_request.opening_name:
            summary_parts.append(f"opening: {filter_request.opening_name}")
        
        if filter_request.event:
            summary_parts.append(f"event: {filter_request.event}")
        
        if filter_request.year:
            summary_parts.append(f"year: {filter_request.year}")
        elif filter_request.date_range:
            summary_parts.append(f"date range: {filter_request.date_range.start_date.year if filter_request.date_range.start_date else '?'}-{filter_request.date_range.end_date.year if filter_request.date_range.end_date else '?'}")
        
        if filter_request.result:
            summary_parts.append(f"result: {filter_request.result}")
        elif filter_request.decisive_only:
            summary_parts.append("decisive games only")
        
        return "; ".join(summary_parts) if summary_parts else "no filters"
    
    def get_filter_suggestions(self, partial_query: str) -> Dict[str, List[str]]:
        """
        Get suggestions for completing a partial filter query
        
        Args:
            partial_query: Partial query string
            
        Returns:
            Dictionary with suggestions by category
        """
        suggestions = {
            "players": [],
            "openings": [],
            "events": [],
            "filters": []
        }
        
        query_lower = partial_query.lower()
        
        # Suggest common filter patterns
        if not query_lower:
            suggestions["filters"] = [
                "games by Carlsen",
                "ELO above 2600",
                "Sicilian Defense games",
                "World Championship",
                "games from 2020"
            ]
        
        # Suggest players based on partial input
        for player in self.common_players:
            if query_lower in player or player.startswith(query_lower):
                suggestions["players"].append(player.title())
        
        # Suggest openings
        for opening in self.opening_patterns.keys():
            if query_lower in opening or opening.startswith(query_lower):
                suggestions["openings"].append(opening.title())
        
        # Get suggestions from the filtering service
        try:
            if len(query_lower) > 2:
                if any(word in query_lower for word in ['player', 'carlsen', 'anand', 'magnus']):
                    player_suggestions = self.filtering_service.get_filter_suggestions(query_lower, "player")
                    suggestions["players"].extend(player_suggestions[:5])
                
                if any(word in query_lower for word in ['opening', 'sicilian', 'ruy', 'french']):
                    opening_suggestions = self.filtering_service.get_filter_suggestions(query_lower, "opening")
                    suggestions["openings"].extend(opening_suggestions[:5])
                
                if any(word in query_lower for word in ['tournament', 'championship', 'event']):
                    event_suggestions = self.filtering_service.get_filter_suggestions(query_lower, "event")
                    suggestions["events"].extend(event_suggestions[:5])
        
        except Exception as e:
            self.logger.error(f"Error getting filter suggestions: {e}")
        
        # Remove duplicates and limit results
        for key in suggestions:
            suggestions[key] = list(dict.fromkeys(suggestions[key]))[:10]
        
        return suggestions
    
    def detect_contextual_filter_request(self, query: str) -> bool:
        """
        Detect if the query is asking to filter previous search results
        
        Args:
            query: User query string
            
        Returns:
            True if this appears to be a contextual filter request
        """
        query_lower = query.lower().strip()
        
        # Contextual filter indicators
        contextual_phrases = [
            "filter these", "from these", "these games", "these results",
            "narrow down", "refine", "add filter", "also filter",
            "among these", "within these", "from the above",
            "from those", "those games", "those results",
            "apply filter", "additional filter", "further filter"
        ]
        
        # Check for contextual phrases
        for phrase in contextual_phrases:
            if phrase in query_lower:
                return True
        
        # Check for filter-only patterns (no explicit search terms)
        filter_only_patterns = [
            r'^(?:show|find|get)?\s*(?:games?\s+)?(?:with|where|having)\s+(?:elo|rating|players?)',
            r'^(?:elo|rating)\s+(?:above|below|over|under)',
            r'^players?\s+(?:rated|with\s+elo)',
            r'^(?:white|black)\s+(?:elo|rating)',
            r'^(?:both\s+)?players?\s+(?:above|below|over|under)',
        ]
        
        for pattern in filter_only_patterns:
            if re.search(pattern, query_lower):
                # This looks like a filter-only request
                return True
        
        return False
    
    def apply_filters_to_results(self, games: List[Dict[str, Any]], 
                                filter_request: GameFilterRequest) -> List[Dict[str, Any]]:
        """
        Apply filters to a list of game results
        
        Args:
            games: List of game dictionaries
            filter_request: Filter criteria to apply
            
        Returns:
            Filtered list of games
        """
        filtered_games = []
        
        for game in games:
            if self._game_matches_filters(game, filter_request):
                filtered_games.append(game)
        
        self.logger.info(f"Applied contextual filters: {len(games)} → {len(filtered_games)} games")
        return filtered_games
    
    def _game_matches_filters(self, game: Dict[str, Any], filter_request: GameFilterRequest) -> bool:
        """Check if a game matches the filter criteria"""
        
        # ELO filters
        if filter_request.white_elo_range or filter_request.black_elo_range:
            white_elo = game.get('white_elo') or game.get('WhiteElo')
            black_elo = game.get('black_elo') or game.get('BlackElo')
            
            # Convert to float if string
            try:
                if white_elo and isinstance(white_elo, str):
                    white_elo = float(white_elo)
                if black_elo and isinstance(black_elo, str):
                    black_elo = float(black_elo)
            except (ValueError, TypeError):
                white_elo = None
                black_elo = None
            
            # Check white ELO range
            if filter_request.white_elo_range:
                if not white_elo:
                    return False
                if filter_request.white_elo_range.min_elo and white_elo < filter_request.white_elo_range.min_elo:
                    return False
                if filter_request.white_elo_range.max_elo and white_elo > filter_request.white_elo_range.max_elo:
                    return False
            
            # Check black ELO range
            if filter_request.black_elo_range:
                if not black_elo:
                    return False
                if filter_request.black_elo_range.min_elo and black_elo < filter_request.black_elo_range.min_elo:
                    return False
                if filter_request.black_elo_range.max_elo and black_elo > filter_request.black_elo_range.max_elo:
                    return False
        
        # Player filters
        if filter_request.white_player:
            white_player = game.get('white_player') or game.get('White', '')
            if filter_request.white_player.lower() not in white_player.lower():
                return False
        
        if filter_request.black_player:
            black_player = game.get('black_player') or game.get('Black', '')
            if filter_request.black_player.lower() not in black_player.lower():
                return False
        
        if filter_request.any_player:
            white_player = game.get('white_player') or game.get('White', '')
            black_player = game.get('black_player') or game.get('Black', '')
            player_name = filter_request.any_player.lower()
            if (player_name not in white_player.lower() and 
                player_name not in black_player.lower()):
                return False
        
        # Event filters
        if filter_request.event:
            event = game.get('event') or game.get('Event', '')
            if filter_request.event.lower() not in event.lower():
                return False
        
        # ECO filters
        if filter_request.eco_code:
            eco = game.get('eco') or game.get('ECO', '')
            if not eco.startswith(filter_request.eco_code):
                return False
        
        # Result filters
        if filter_request.result:
            result = game.get('result') or game.get('Result', '')
            if result != filter_request.result:
                return False
        
        # Date filters
        if filter_request.year:
            date_str = game.get('date') or game.get('Date', '')
            if str(filter_request.year) not in date_str:
                return False
        
        return True
    
    def _extract_core_query(self, query: str) -> Tuple[str, str]:
        """
        Extract core query from language-prefixed queries and detect language.
        
        Args:
            query: The input query (possibly with language prefix)
            
        Returns:
            Tuple of (core_query, detected_language)
        """
        # Check for language prefix patterns
        language_prefixes = [
            (r'Please respond in Russian language\. User query: (.+)', 'ru'),
            (r'Please respond in English language\. User query: (.+)', 'en'),
            (r'Отвечай на русском языке\. Запрос пользователя: (.+)', 'ru'),
        ]
        
        for pattern, lang in language_prefixes:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip(), lang
        
        # Auto-detect language if no prefix found
        detected_lang = self._detect_language(query)
        return query.strip(), detected_lang
    
    def _detect_language(self, text: str) -> str:
        """
        Detect language of the text.
        
        Args:
            text: Input text
            
        Returns:
            Language code ('ru' for Russian, 'en' for English)
        """
        if not text:
            return 'en'
        
        # Count Cyrillic characters
        cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        total_letters = sum(1 for char in text if char.isalpha())
        
        # If more than 30% of alphabetic characters are Cyrillic, consider it Russian
        if total_letters > 0 and (cyrillic_count / total_letters) > 0.3:
            return 'ru'
        
        return 'en'
    
    def _matches_multilingual_patterns(self, query: str, pattern_category: str, language: str) -> bool:
        """
        Check if query matches multilingual patterns for a given category.
        
        Args:
            query: The query to check
            pattern_category: Category from self.language_patterns
            language: Language code ('en', 'ru')
            
        Returns:
            True if query matches patterns in the category
        """
        if pattern_category not in self.language_patterns:
            return False
        
        patterns = self.language_patterns[pattern_category].get(language, [])
        query_lower = query.lower()
        
        return any(pattern in query_lower for pattern in patterns)
    
    def classify_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify query and update state - compatible with orchestrator
        
        This method provides compatibility with the existing orchestrator while
        adding enhanced contextual filtering capabilities.
        
        Args:
            state: RagState dictionary containing user_query and other context
            
        Returns:
            Updated state dictionary with query classification and metadata
        """
        query = state.get("user_query", "")
        current_fen = state.get("current_board_fen")
        
        self.logger.info(f"EnhancedRouterAgent classifying query: '{query[:50]}...'")
        
        # Extract core query and detect language
        core_query, detected_language = self._extract_core_query(query)
        self.logger.info(f"Core query: '{core_query[:50]}...', Language: {detected_language}")
        
        # First check if this is a contextual filter request
        if self.detect_contextual_filter_request(core_query):
            self.logger.info("Detected contextual filter request")
            state["query_type"] = "contextual_filter"
            state["router_metadata"] = {
                "is_contextual_filter": True,
                "filter_request": self.parse_filter_query(core_query),
                "detected_language": detected_language
            }
            return state
        
        # Check if this is a game search with filters
        filter_request = self.parse_filter_query(core_query)
        if self._has_meaningful_filters(filter_request):
            self.logger.info("Detected game search with filters")
            state["query_type"] = "game_search"
            state["game_filters"] = filter_request
            
            # CRITICAL FIX: Use extracted FEN from filter_request if available, otherwise fall back to current_fen
            extracted_fen = filter_request.fen_position if hasattr(filter_request, 'fen_position') and filter_request.fen_position else current_fen
            
            state["router_metadata"] = {
                "has_filters": True,
                "filter_request": filter_request,
                "fen_for_game_search": extracted_fen,  # Use extracted FEN, not just current_fen
                "detected_language": detected_language
            }
            
            self.logger.info(f"Game search FEN: extracted='{filter_request.fen_position}', current='{current_fen}', using='{extracted_fen}'")
            return state
        
        # Fallback to basic classification logic using multilingual patterns
        
        # Check for opening-related queries
        if self._matches_multilingual_patterns(core_query, 'opening_lookup', detected_language):
            state["query_type"] = "opening_lookup"
            if current_fen:
                state["fen_for_analysis"] = current_fen
            state["router_metadata"] = {
                "fen_for_analysis": current_fen,
                "detected_language": detected_language
            }
            return state
        
        # Check for position analysis queries
        if self._matches_multilingual_patterns(core_query, 'position_analysis', detected_language):
            state["query_type"] = "position_analysis"
            if current_fen:
                state["fen_for_analysis"] = current_fen
            state["router_metadata"] = {
                "fen_for_analysis": current_fen,
                "detected_language": detected_language
            }
            return state
        
        # Check for game search queries (including position-related searches)
        if (self._matches_multilingual_patterns(core_query, 'game_search', detected_language) or 
            self._matches_multilingual_patterns(core_query, 'position_related', detected_language)):
            state["query_type"] = "game_search"
            state["game_filters"] = filter_request  # Even if empty, might have basic search
            
            # CRITICAL FIX: Use extracted FEN from filter_request if available, otherwise fall back to current_fen
            extracted_fen = filter_request.fen_position if hasattr(filter_request, 'fen_position') and filter_request.fen_position else current_fen
            
            state["router_metadata"] = {
                "has_basic_search": True,
                "fen_for_game_search": extracted_fen,  # Use extracted FEN, not just current_fen
                "detected_language": detected_language
            }
            
            self.logger.info(f"Basic game search FEN: extracted='{filter_request.fen_position}', current='{current_fen}', using='{extracted_fen}'")
            return state
        
        # Check for move history queries
        if self._matches_multilingual_patterns(core_query, 'move_history', detected_language):
            state["query_type"] = "move_history_lookup"
            state["router_metadata"] = {"detected_language": detected_language}
            return state
        
        # Default to semantic search
        state["query_type"] = "semantic"
        if current_fen:
            state["fen_for_analysis"] = current_fen
        state["router_metadata"] = {
            "fen_for_analysis": current_fen,
            "detected_language": detected_language,
            "core_query": core_query
        }
        
        self.logger.info(f"Classified as '{state['query_type']}' with metadata: {state.get('router_metadata', {})}")
        return state
    
    def _has_meaningful_filters(self, filter_request: GameFilterRequest) -> bool:
        """
        Check if the filter request has meaningful filtering criteria
        
        Args:
            filter_request: GameFilterRequest object to check
            
        Returns:
            True if the request has meaningful filters
        """
        if not filter_request:
            return False
        
        # Check for any meaningful filter criteria
        meaningful_criteria = [
            filter_request.white_player,
            filter_request.black_player,
            filter_request.any_player,
            filter_request.white_elo_range,
            filter_request.black_elo_range,
            filter_request.date_range,
            filter_request.event,
            filter_request.opening_name,
            filter_request.result,
            filter_request.time_control,
            filter_request.white_title,
            filter_request.black_title
        ]
        
        return any(criteria is not None for criteria in meaningful_criteria) 