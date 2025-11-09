from typing import Literal, Dict, Any, TypedDict, Optional, List

class RagState(TypedDict, total=False): # total=False allows for fields to be added incrementally
    # Core pipeline inputs
    user_query: str
    current_board_fen: Optional[str]
    session_pgn: Optional[str] # ADDED: PGN string of the current session's game
    answer_agent_instance: Any # Instance of AnswerAgent, can't type directly due to import cycle potential with __init__

    # Router Agent Output / Intermediate State
    query_type: Literal[
        "fen", "diagram", "semantic", "board_update", 
        "opening_lookup", "stockfish_analysis_needed", "lesson_lookup_topic",
        "game_search",  # Added for FEN-based game searches
        "error" # For internal errors
    ]
    fen_for_analysis: Optional[str]
    diagram_number: Optional[int]
    topic_for_lesson_lookup: Optional[str]
    # Can add other specific metadata extracted by router
    router_metadata: Dict[str, Any] # General metadata from router

    # Specialist Agent Outputs / Accumulated Context
    retrieved_chunks: List[Dict[str, Any]]
    # Specific structured data from agents (optional, can also go into retrieved_chunks with a type)
    opening_data: Optional[Dict[str, Any]]
    stockfish_analysis_data: Optional[Dict[str, Any]]
    lesson_data: List[Dict[str, Any]]
    game_filters: Optional[Dict[str, Any]] # ADDED: Filters for game search (e.g., player, ECO)
    retrieved_games: Optional[List[Dict[str, Any]]] # ADDED: List of games from GameSearchAgent

    # Final Output
    final_answer: Optional[str]
    error_message: Optional[str] 