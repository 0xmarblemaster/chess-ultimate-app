import re
from typing import Literal, Dict, Any, TypedDict, Optional
# Import RagState from shared_types
from .shared_types import RagState
import logging # Ensure logging is imported
import chess
import sys
import os
# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from llm.openai_llm import OpenAILLM

# RouterAgentOutput is no longer needed as classify_query will modify RagState directly

# Get a logger instance (or use print for simplicity if logging isn't set up)
logger = logging.getLogger(__name__)
# If logging isn't configured, print statements can be used instead:
# def print_debug(msg): print(f"DEBUG: [RouterAgent] {msg}")

# Utility function - can remain at module level or be a static method
def extract_fen_from_query(query: str) -> Optional[str]:
    # Basic FEN regex (simplified, might need to be more robust)
    # Matches standard FEN, permissive of missing clock/move counters
    fen_pattern = r"([rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}\s+[wb]\s+([KQkq]{1,4}|-)\s+(-|[a-h][1-8])(\s+\d+\s+\d+)?)"
    match = re.search(fen_pattern, query)
    if match:
        return match.group(0).strip()  # Return the full match, not just group 1
    return None

class RouterAgent:
    def __init__(self, llm_client: Optional[OpenAILLM] = None):
        """
        Initializes the RouterAgent.
        Args:
            llm_client: An optional LLM client instance, for future use if routing becomes LLM-driven.
        """
        self.llm_client = llm_client # Store for potential future use
        logger.info(f"RouterAgent initialized. LLM Client provided: {bool(llm_client)}")

    def classify_query(self, state: RagState) -> RagState:
        """
        Classifies a user query to determine the appropriate agent to handle it.
        Updates the RagState with query_type and relevant metadata.
        
        Args:
            state: The current RagState object.
            
        Returns:
            The modified RagState object.
        """
        initial_query_original_case = state.get("user_query", "")
        initial_query = initial_query_original_case.lower() # Work with lowercase for keyword matching
        
        current_board_fen = state.get("current_board_fen") or \
                            state.get("current_fen") or \
                            (state.get("router_metadata", {}).get("current_board_fen"))

        logger.info(f"RouterAgent Classifying Query. Initial query: '{initial_query_original_case}', Current Board FEN: '{current_board_fen}'")

        state["router_metadata"] = state.get("router_metadata", {}) 
        state["fen_for_analysis"] = None
        state["diagram_number"] = None
        state["query_type"] = "semantic" # Default
        
        # 0. Check for non-chess queries first (direct questions that don't need database retrieval)
        non_chess_keywords = [
            # Math and arithmetic
            "what is", "calculate", "add", "subtract", "multiply", "divide", "plus", "minus", "times", "equals",
            # General knowledge
            "explain", "define", "what does", "how does", "why does", "tell me about",
            # Simple greetings and commands
            "hello", "hi", "thanks", "thank you", "help", "how are you"
        ]
        
        # Check for simple direct questions that should NOT trigger retrieval
        simple_direct_patterns = [
            # Simple FEN/board queries (questions)
            r"^what\s+is\s+the\s+current\s+(board\s+)?fen\s*\??$",
            r"^(show|tell|give)\s+me\s+the\s+current\s+(board\s+)?fen\s*\??$",
            r"^current\s+(board\s+)?fen\s*\??$",
            r"^get\s+current\s+(board\s+)?fen\s*\??$",
            
            # Simple board status queries  
            r"^what\s+is\s+the\s+current\s+board\s*\??$",
            r"^(show|tell|give)\s+me\s+the\s+current\s+board\s*\??$",
            r"^current\s+board\s*\??$",
            
            # Simple position queries without analysis intent
            r"^what\s+is\s+the\s+current\s+position\s*\??$",
            r"^(show|tell|give)\s+me\s+the\s+current\s+position\s*\??$",
            r"^current\s+position\s*\??$",
            
            # ADDED: Informational statements about FEN/position (not questions)
            r"^the\s+current\s+(board\s+)?fen\s+is\s*:?\s*",
            r"^current\s+(board\s+)?fen\s*:?\s*",
            r"^the\s+(current\s+)?position\s+is\s*:?\s*",
            r"^the\s+(current\s+)?board\s+is\s*:?\s*",
            r"^this\s+position\s+represents\s*",
            r"^this\s+is\s+the\s+(starting\s+)?position\s+(after|with)\s*",
            r"^here\s+is\s+the\s+(current\s+)?(fen|position|board)\s*:?\s*",
            
            # ADDED: Simple descriptive statements about moves and positions  
            r"^(after|with)\s+the\s+move\s+[a-h]?[1-8]?\s*\.?\s*[a-zA-Z0-9\+\#\=]+.*black\s+to\s+move",
            r"^(after|with)\s+the\s+move\s+[a-h]?[1-8]?\s*\.?\s*[a-zA-Z0-9\+\#\=]+.*white\s+to\s+move",
            
            # ADDED: More comprehensive descriptive statements about positions after moves
            r"^this\s+is\s+the\s+starting\s+position\s+after\s+the\s+move\s+[a-h]?[1-8]?\s*\.?\s*[a-zA-Z0-9\+\#\=]+.*",
            r"^this\s+is\s+the\s+position\s+after\s+[a-h]?[1-8]?\s*\.?\s*[a-zA-Z0-9\+\#\=]+.*",
            r"^this\s+shows\s+the\s+position\s+after\s+[a-h]?[1-8]?\s*\.?\s*[a-zA-Z0-9\+\#\=]+.*",
        ]
        
        # Check if query matches simple direct patterns
        for pattern in simple_direct_patterns:
            if re.search(pattern, initial_query, re.IGNORECASE):
                state["query_type"] = "direct"
                logger.info(f"Classified as 'direct' (simple FEN/board query): '{initial_query_original_case}'")
                return state
        
        # Check if query contains chess-related terms
        chess_terms = [
            "chess", "fen", "opening", "game", "games", "move", "moves", "position", "board", 
            "piece", "pieces", "pawn", "rook", "knight", "bishop", "queen", "king",
            "castle", "castling", "check", "checkmate", "stalemate", "draw", "resign",
            "white", "black", "player", "tournament", "eco", "pgn", "diagram"
        ]
        
        has_chess_terms = any(term in initial_query for term in chess_terms)
        has_non_chess_pattern = any(keyword in initial_query for keyword in non_chess_keywords)
        
        # For general non-chess questions (without chess terms), classify as direct
        if has_non_chess_pattern and not has_chess_terms:
            state["query_type"] = "direct"
            logger.info(f"Classified as 'direct' (general non-chess query): '{initial_query_original_case}'")
            return state

        # 1. Board update with explicit FEN
        board_update_keywords = ["set board to fen", "update to", "load fen", "set board fen", "board fen is"]
        for keyword in board_update_keywords:
            if initial_query.startswith(keyword.lower()):
                extracted_fen = extract_fen_from_query(initial_query_original_case) 
                if extracted_fen:
                    state["query_type"] = "board_update"
                    state["router_metadata"]["fen"] = extracted_fen
                    state["fen_for_analysis"] = extracted_fen
                    logger.info(f"Classified as 'board_update'. FEN: {extracted_fen}")
                    return state

        # 2. Diagram lookup
        diagram_match = re.search(r"diagram\\s*(?:#)?(\\d+)", initial_query)
        if diagram_match:
            diagram_num = int(diagram_match.group(1))
            state["query_type"] = "diagram_lookup" # More specific type
            state["diagram_number"] = diagram_num
            state["router_metadata"]["diagram_number"] = diagram_num
            logger.info(f"Classified as 'diagram_lookup'. Diagram #: {diagram_num}")
            return state

        # 3. Explicit opening lookup
        opening_interrogatives = [
            r"what.*opening", r"name.*opening", r"identify.*opening", 
            r"call(ed)?.*opening", r"how is .* opening called", r"which.*opening"
        ]
        if "opening" in initial_query and any(re.search(p, initial_query) for p in opening_interrogatives):
            state["query_type"] = "opening_lookup"
            fen_in_query = extract_fen_from_query(initial_query_original_case) 
            if fen_in_query:
                state["fen_for_analysis"] = fen_in_query
                state["router_metadata"]["fen_for_analysis"] = fen_in_query
                logger.info(f"Classified as 'opening_lookup'. FEN from query: {fen_in_query}")
            elif current_board_fen:
                state["fen_for_analysis"] = current_board_fen
                state["router_metadata"]["fen_for_analysis"] = current_board_fen
                logger.info(f"Classified as 'opening_lookup'. FEN from GUI: {current_board_fen}")
            else:
                logger.info(f"Classified as 'opening_lookup'. No immediate FEN found.")
            return state

        # 4. Move history / PGN request
        move_history_keywords = [
            "move history", "list moves", "show moves", "game history",
            "what were the moves", "pgn", "portable game notation",
            "game record", "moves played"
        ]
        if any(keyword in initial_query for keyword in move_history_keywords):
            state["query_type"] = "move_history_lookup"
            if not state.get("fen_for_analysis") and current_board_fen:
                state["fen_for_analysis"] = current_board_fen
                state["router_metadata"]["fen_for_analysis"] = current_board_fen
            logger.info(f"Classified as 'move_history_lookup'. FEN for analysis: {state.get('fen_for_analysis')}")
            return state

        # 5. Position analysis intent (MUST come before game search)
        position_analysis_keywords = [
            "best move", "what move", "recommend move", "suggest move", "next move",
            "analyze", "analysis", "evaluate", "evaluation", "assess", "assessment",
            "what should", "what to play", "how to play", "what's the best",
            "engine", "stockfish", "computer move", "engine move",
            "position eval", "static eval", "score", "advantage",
            "tactics", "tactical", "combination", "threat", "threats"
        ]
        
        is_position_analysis = any(keyword in initial_query for keyword in position_analysis_keywords)
        
        # Additional patterns for position analysis
        analysis_patterns = [
            r"what.*move.*for.*white",
            r"what.*move.*for.*black", 
            r"best.*move.*white",
            r"best.*move.*black",
            r"should.*white.*play",
            r"should.*black.*play",
            r"how.*white.*continue",
            r"how.*black.*continue",
            r"evaluate.*position",
            r"analyze.*position"
        ]
        
        for pattern in analysis_patterns:
            if re.search(pattern, initial_query):
                is_position_analysis = True
                break
        
        if is_position_analysis:
            state["query_type"] = "position_analysis"
            
            # Check if user is referring to "current" position - prioritize current board FEN over query FEN
            current_position_keywords = ["current", "this position", "this board", "current board", "current fen"]
            is_referring_to_current = any(keyword in initial_query for keyword in current_position_keywords)
            
            # Determine which FEN to use for analysis
            fen_in_query = extract_fen_from_query(initial_query_original_case)
            if fen_in_query and not is_referring_to_current:
                state["fen_for_analysis"] = fen_in_query
                state["router_metadata"]["fen_for_analysis"] = fen_in_query
                logger.info(f"Classified as 'position_analysis'. FEN from query: {fen_in_query}")
            elif current_board_fen:
                state["fen_for_analysis"] = current_board_fen
                state["router_metadata"]["fen_for_analysis"] = current_board_fen
                logger.info(f"Classified as 'position_analysis'. FEN from current board: {current_board_fen}")
            else:
                logger.info(f"Classified as 'position_analysis'. No FEN found.")
            
            return state

        # 6. Game search intent
        game_search_keywords = [
            "find game", "search game", "look for game", "show game", "any game",
            "find games", "search games", "look for games", "show games", "any games",  # Added plural forms
            "games by", "games with", "game played by", "games played by",
            "database for this fen", "games for this fen", "search fen",
            "games in this position", "games with this position", "position games",  # Added position-based searches
            # ELO filtering keywords
            "filter by elo", "filter elo", "elo above", "elo below", "elo higher", "elo lower",
            "elo greater", "elo less", "elo >", "elo <", "elo between", "rated above", "rated below",
            "rated higher", "rated lower", "rated over", "rated under", "rating above", "rating below",
            "games with elo", "players rated", "filter by rating", "filter rating",
            # Russian game search keywords
            "найди партии", "найди игры", "ищи партии", "ищи игры", "поиск партий", "поиск игр",
            "найди партию", "найди игру", "ищи партию", "ищи игру", "поиск партии", "поиск игры",
            "покажи партии", "покажи игры", "покажи партию", "покажи игру",
            "партии с", "игры с", "партии в", "игры в", "партии для", "игры для",
            "партии по", "игры по", "партии этой", "игры этой", "партии данной", "игры данной",
            "партии с позицией", "игры с позицией", "партии в позиции", "игры в позиции",
            "партии с этим", "игры с этим", "партии с данной", "игры с данной",
            # Kazakh game search keywords
            "ойындарды тап", "ойындар тап", "ойындарды іздеу", "ойындар іздеу", "ойын тап", "ойын іздеу",
            "ойындарды көрсет", "ойындар көрсет", "ойын көрсет", "ойынды көрсет",
            "ойындарды ал", "ойындар ал", "ойынды ал", "ойын ал",
            "ойындар арқылы", "ойындармен", "ойын арқылы", "ойынмен",
            "ойындарды позициямен", "ойындар позициямен", "ойын позициямен",
            "осы позициядағы ойындар", "осы позициядағы ойын", "позициядағы ойындар", "позициядағы ойын",
            "ойындар базасы", "ойын базасы", "база ойындар", "база ойын",
            "ойындарды fen", "ойындар fen", "fen ойындар", "fen ойын"
        ]
        game_filters = {}
        is_game_search_query = any(keyword in initial_query for keyword in game_search_keywords)
        fen_directly_in_query_for_gs = extract_fen_from_query(initial_query_original_case)

        # Check if user is referring to "current" position - prioritize current board FEN over query FEN
        current_position_keywords = ["current", "this position", "this board", "current board", "current fen"]
        is_referring_to_current = any(keyword in initial_query for keyword in current_position_keywords)

        if fen_directly_in_query_for_gs and not is_referring_to_current:
            simplified_query = re.sub(r'\s+', '', initial_query)
            simplified_fen = re.sub(r'\s+', '', fen_directly_in_query_for_gs.lower())
            # Add Russian keywords for game search detection
            game_search_trigger_keywords = ["search", "find", "get", "database", "games", "найди", "ищи", "поиск", "партии", "игры"]
            if simplified_fen in simplified_query and (any(kw in initial_query for kw in game_search_trigger_keywords) or len(initial_query_original_case.split()) < 7):
                is_game_search_query = True
                logger.info(f"FEN directly in query ('{fen_directly_in_query_for_gs}') triggered game_search classification.")
        elif is_referring_to_current and current_board_fen:
            # User is asking about current position, ignore any FEN in query text
            is_game_search_query = True
            logger.info(f"User referring to current position, using current board FEN instead of query FEN.")
        
        # Check for "[Player Name] games" pattern (e.g., "Gukesh games", "Carlsen games")
        player_games_pattern = re.search(r'^([a-zA-Z][a-zA-Z\s\.\-]{1,30})\s+games?$', initial_query_original_case.strip(), re.IGNORECASE)
        if player_games_pattern and not is_game_search_query:
            player_name = player_games_pattern.group(1).strip()
            # Avoid false positives with common words
            common_words = ['chess', 'good', 'bad', 'best', 'worst', 'new', 'old', 'recent', 'past', 'future', 'all', 'some', 'many', 'few']
            if player_name.lower() not in common_words:
                is_game_search_query = True
                logger.info(f"Player games pattern matched: '{player_name} games' -> game_search")
        
        if not is_game_search_query:
            if "eco" in initial_query and ("game" in initial_query or "games" in initial_query):
                is_game_search_query = True
            if ("player" in initial_query or "played by" in initial_query) and ("game" in initial_query or "games" in initial_query):
                is_game_search_query = True
            if "event" in initial_query and ("game" in initial_query or "games" in initial_query):
                is_game_search_query = True

        if is_game_search_query:
            state["query_type"] = "game_search"
            logger.info(f"Tentatively classified as 'game_search'. Analyzing for filters...")
            # Simplified filter extraction (can be expanded)
            player_match_white = re.search(r"(?:white is|white:|played by|as white)\s+([a-zA-Z0-9\s\.\-]+)(?:\s+as black|\s+vs|\s+against|\s+and black|\s+black is|\s+black:|$)", initial_query_original_case, re.IGNORECASE)
            if player_match_white and player_match_white.group(1).strip(): game_filters["white_player"] = player_match_white.group(1).strip()
            player_match_black = re.search(r"(?:as black|black is|black:|vs|against)\s+([a-zA-Z0-9\s\.\-]+)(?:\s+as white|\s+and white|\s+white is|\s+white:|$)", initial_query_original_case, re.IGNORECASE)
            if player_match_black and player_match_black.group(1).strip(): 
                if not (game_filters.get("white_player") and game_filters.get("white_player").lower() in player_match_black.group(1).strip().lower()):
                    game_filters["black_player"] = player_match_black.group(1).strip()
            
            # Generic player search patterns
            patterns_to_try = [
                # "Search all games for player NAME"
                r"(?:search all games for player|search games for player|find games for player)\s+([a-zA-Z][a-zA-Z\s\.\-]+?)(?:\s+(?:eco|event|date|fen|as|vs|against)|$)",
                # "games by/with/for NAME"  
                r"(?:games (?:by|with|for))\s+([a-zA-Z][a-zA-Z\s\.\-]+?)(?:\s+(?:eco|event|date|fen|as|vs|against)|$)",
                # "find games by/with/for NAME"
                r"(?:find games (?:by|with|for))\s+([a-zA-Z][a-zA-Z\s\.\-]+?)(?:\s+(?:eco|event|date|fen|as|vs|against)|$)",
                # "search games by/with/for NAME" 
                r"(?:search games (?:by|with|for))\s+([a-zA-Z][a-zA-Z\s\.\-]+?)(?:\s+(?:eco|event|date|fen|as|vs|against)|$)",
                # "player NAME" (generic fallback)
                r"(?:^|\s)player\s+([a-zA-Z][a-zA-Z\s\.\-]+?)(?:\s+(?:eco|event|date|fen|as|vs|against)|$)"
            ]
            
            generic_player_match = None
            for pattern in patterns_to_try:
                generic_player_match = re.search(pattern, initial_query_original_case, re.IGNORECASE)
                if generic_player_match:
                    break
            
            if generic_player_match:
                game_filters["any_player"] = generic_player_match.group(1).strip()
                logger.info(f"Extracted any_player: {game_filters['any_player']}")
            
            # Handle "[Player Name] games" pattern
            if not game_filters.get("any_player") and not game_filters.get("white_player") and not game_filters.get("black_player"):
                player_games_match = re.search(r'^([a-zA-Z][a-zA-Z\s\.\-]{1,30})\s+games?$', initial_query_original_case.strip(), re.IGNORECASE)
                if player_games_match:
                    player_name = player_games_match.group(1).strip()
                    common_words = ['chess', 'good', 'bad', 'best', 'worst', 'new', 'old', 'recent', 'past', 'future', 'all', 'some', 'many', 'few']
                    if player_name.lower() not in common_words:
                        game_filters["any_player"] = player_name
                        logger.info(f"Extracted any_player from pattern: {game_filters['any_player']}")
            
            eco_match = re.search(r"(?:eco|opening code)\s+([A-E][0-9]{0,2})", initial_query, re.IGNORECASE)
            if eco_match: game_filters["eco"] = eco_match.group(1).upper()
            event_match = re.search(r"(?:event|tournament)\s+([\w\s]+?)(?:\s+player|\s+eco|\s+date|$)", initial_query_original_case, re.IGNORECASE)
            if event_match and event_match.group(1).strip(): game_filters["event"] = event_match.group(1).strip()

            # Determine if this is a position-based search or a pure player/metadata search
            position_related_keywords = [
                "position", "this position", "current position", "current board", "this board", 
                "fen", "games for this fen", "games in this position", "games with this position",
                "position games", "database for this fen", "search fen", "current", "this"
            ]
            is_position_based = any(keyword in initial_query.lower() for keyword in position_related_keywords)
            
            # Only set FEN for game search if:
            # 1. User explicitly provided a FEN in the query, OR
            # 2. User is referring to current/this position, OR  
            # 3. User is asking for position-specific searches
            if is_referring_to_current and current_board_fen:
                state["router_metadata"]["fen_for_game_search"] = current_board_fen
                state["fen_for_analysis"] = current_board_fen
                logger.info(f"Using current board FEN for game search: {current_board_fen}")
            elif fen_directly_in_query_for_gs and not is_referring_to_current:
                state["router_metadata"]["fen_for_game_search"] = fen_directly_in_query_for_gs
                state["fen_for_analysis"] = fen_directly_in_query_for_gs
                logger.info(f"Using FEN from query for game search: {fen_directly_in_query_for_gs}")
            elif is_position_based and current_board_fen:
                state["router_metadata"]["fen_for_game_search"] = current_board_fen
                state["fen_for_analysis"] = current_board_fen
                logger.info(f"Using current board FEN for position-based search: {current_board_fen}")
            else:
                # Pure player/metadata search - don't add position filtering
                logger.info(f"Pure player/metadata search - no FEN filtering applied")
            
            if game_filters: state["game_filters"] = game_filters
            logger.info(f"Classified as 'game_search'. Filters: {state.get('game_filters')}, FEN for analysis: {state.get('fen_for_analysis')}")
            return state

        # 7. Query contains FEN for general analysis (not already game_search)
        fen_in_query_general = extract_fen_from_query(initial_query_original_case)
        if fen_in_query_general and state["query_type"] != "game_search": # Avoid re-assigning if game_search already used it
            if state["query_type"] == "semantic" or state.get("fen_for_analysis") != fen_in_query_general:
                state["fen_for_analysis"] = fen_in_query_general
                state["router_metadata"]["fen_for_analysis"] = fen_in_query_general
                logger.info(f"FEN found in query: {fen_in_query_general}. Set for general analysis. Query type '{state['query_type']}'.")

        # 8. If semantic query, no FEN in query, but current_board_fen exists, use it.
        if state["query_type"] == "semantic" and not state.get("fen_for_analysis") and current_board_fen:
            state["fen_for_analysis"] = current_board_fen
            state["router_metadata"]["fen_for_analysis"] = current_board_fen
            logger.info(f"Using current_board_fen ('{current_board_fen}') for semantic query context.")

        # Fallback to semantic if no other type matched, or if it was the default.
        if state["query_type"] == "semantic":
            logger.info(f"Classified as 'semantic' (default/fallback). FEN for analysis (if any): {state['fen_for_analysis']}")
        
        # Log final decision for this path
        logger.info(f"RouterAgent final classification. Query Type: '{state['query_type']}', FEN for Analysis: '{state['fen_for_analysis']}', Diagram#: {state.get('diagram_number')}, GameFilters: {state.get('game_filters')}")
        return state

# Example usage (for testing this module directly if needed)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    test_router_agent = RouterAgent() # No LLM client needed for current logic

    queries_to_test = [
        ("set board to fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
        ("show diagram 5", None),
        ("what opening is this?", "rnbqkbnr/pp1ppppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"),
        ("tell me the PGN for this game", "r1bqkbnr/pp1ppppp/2n5/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"),
        ("find games by Magnus Carlsen as white with ECO C65", None),
        ("search for games with FEN r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3", None),
        ("explain the Najdorf variation", None),
        ("what is the best move for white in rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1?", None),
        ("analyze this position: 2k5/5R2/8/8/8/8/8/K7 w - - 0 1", None)
    ]

    for query_text, fen_context in queries_to_test:
        print(f"\n--- Testing Query: '{query_text}', Context FEN: {fen_context} ---")
        initial_state: RagState = {
            "user_query": query_text,
            "current_board_fen": fen_context,
            "raw_user_query": query_text, # Assuming raw query is same as user_query for this test
            "chat_history": [],
            "retrieved_chunks": [],
            "answer_parts": [],
            "final_answer": None,
            "error_message": None,
            "query_type": None, # Will be set by router
            "router_metadata": {},
            "fen_for_analysis": None,
            "diagram_number": None,
            "game_filters": None,
            "session_pgn": None
        }
        
        # Ensure current_fen is also set in router_metadata if current_board_fen exists
        if fen_context:
            initial_state["router_metadata"]["current_board_fen"] = fen_context
            
        result_state = test_router_agent.classify_query(initial_state)
        print(f"Resulting State: Query Type='{result_state.get('query_type')}', FEN Analysis='{result_state.get('fen_for_analysis')}', Diagram='{result_state.get('diagram_number')}', GameFilters='{result_state.get('game_filters')}', Metadata='{result_state.get('router_metadata')}'") 