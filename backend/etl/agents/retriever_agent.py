from typing import Dict, Any, List, Optional
import re
import json
import logging

from .. import config as etl_config_module
from ..weaviate_loader import get_weaviate_client, search_weaviate
# Use ChessGame collection for all data since that's what exists
CHESS_OPENING_CLASS_NAME = "ChessGame"
import sys
import os
# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from stockfish_analyzer import analyze_fen_with_stockfish
from weaviate import Client as WeaviateSDKClient
from ..utils.opening_book_utils import query_opening_book_by_fen
from .shared_types import RagState
from .game_search_agent import find_games_by_criteria

try:
    from .context_manager import extract_chess_context, ChessContext
except ImportError:
    from context_manager import extract_chess_context, ChessContext

try:
    from .enhanced_retriever import EnhancedRetriever, RetrievalResult
except ImportError:
    from enhanced_retriever import EnhancedRetriever, RetrievalResult

try:
    from .advanced_rag_integration import create_advanced_rag_retriever
except ImportError:
    from advanced_rag_integration import create_advanced_rag_retriever

try:
    from .performance_monitor import performance_monitor
except ImportError:
    from performance_monitor import performance_monitor

# Add import for unified filter system
from .unified_filter_system import UnifiedFilterSystem

logger = logging.getLogger(__name__)

# Regex for FEN validation and extraction
FEN_REGEX = re.compile(r'([rnbqkpRNBQKP1-8]+/){7}([rnbqkpRNBQKP1-8]+)\s+(w|b)\s+(-|K?Q?k?q?)\s+(-|[a-h][36])\s+(\d+)\s+(\d+)')

def extract_fen_from_query(query: str) -> Optional[str]:
    """Extracts the first FEN string found in a query."""
    match = FEN_REGEX.search(query)
    if match:
        return match.group(0)
    return None

# Helper to identify FEN-like strings
def is_fen_like(text: str) -> bool:
    # Uses the more robust FEN_REGEX for matching
    return FEN_REGEX.fullmatch(text.strip()) is not None

def normalize_fen_for_matching(fen: str) -> str:
    """
    Normalizes a FEN string for better matching by handling en passant variations.
    
    Args:
        fen: The FEN string to normalize
        
    Returns:
        Normalized FEN string
    """
    if not fen:
        return fen
        
    parts = fen.strip().split()
    if len(parts) < 4:
        return fen
        
    # Keep board position, active color, castling rights
    # But normalize en passant to '-' for matching purposes
    normalized_parts = parts[:3] + ['-'] + parts[4:]
    return ' '.join(normalized_parts)

def retrieve_by_fen(fen: str, limit: int = 25) -> List[Dict[str, Any]]:
    """
    Retrieves chess games, lesson chunks, and opening data by FEN.
    Fixed to use actual ChessGame schema properties: all_ply_fens, final_fen, mid_game_fen
    Updated default limit from 5 to 25 to reflect expanded database (53,884 games)
    Now uses normalized FEN matching for better position search
    """
    if not fen or not fen.strip():
        return []
    
    fen = fen.strip()
    normalized_search_fen = normalize_fen_for_matching(fen)
    all_matching_items = []
    
    client = get_weaviate_client()
    if not client:
        print("Could not connect to Weaviate")
        return []
    
    try:
        # === SEARCH CHESSGAME COLLECTION FOR FEN MATCHES ===
        try:
            import weaviate.classes.query as weaviate_query
            game_collection = client.collections.get("ChessGame")
            print(f"DEBUG: Searching for FEN: {fen}")
            print(f"DEBUG: Normalized FEN: {normalized_search_fen}")
            
            # Check if this is the starting position (special case)
            starting_position_normalized = normalize_fen_for_matching("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            is_starting_position = normalized_search_fen == starting_position_normalized
            
            found_games = []
            
            if is_starting_position:
                # Starting position: all games have this, so return a sample
                print("DEBUG: Searching for starting position - returning sample games")
                sample_result = game_collection.query.fetch_objects(limit=limit)
                if sample_result and sample_result.objects:
                    found_games = sample_result.objects
                    print(f"DEBUG: Found {len(found_games)} sample games for starting position")
            else:
                # Strategy 1: Search for exact FEN match first
                fen_result = game_collection.query.fetch_objects(
                    filters=weaviate_query.Filter.by_property("all_ply_fens").contains_any([fen]),
                    limit=limit
                )
                
                if fen_result and fen_result.objects:
                    found_games.extend(fen_result.objects)
                    print(f"DEBUG: Found {len(fen_result.objects)} games with exact FEN in all_ply_fens")
                
                # Strategy 2: If no exact matches, search for normalized FEN
                if not found_games:
                    normalized_result = game_collection.query.fetch_objects(
                        filters=weaviate_query.Filter.by_property("all_ply_fens").contains_any([normalized_search_fen]),
                        limit=limit
                    )
                    
                    if normalized_result and normalized_result.objects:
                        found_games.extend(normalized_result.objects)
                        print(f"DEBUG: Found {len(normalized_result.objects)} games with normalized FEN in all_ply_fens")
                
                # Strategy 3: Search by position similarity (first 4 parts of FEN)
                if not found_games:
                    # Extract just the board position and active color for broader search
                    fen_parts = fen.split()
                    if len(fen_parts) >= 2:
                        position_pattern = f"{fen_parts[0]} {fen_parts[1]}"
                        print(f"DEBUG: Searching for position pattern: {position_pattern}")
                        
                        # Get a larger sample and filter manually for position matches
                        broad_result = game_collection.query.fetch_objects(limit=100)
                        
                        if broad_result and broad_result.objects:
                            for game_obj in broad_result.objects:
                                all_ply_fens = game_obj.properties.get("all_ply_fens", [])
                                for game_fen in all_ply_fens:
                                    game_fen_parts = game_fen.split()
                                    if len(game_fen_parts) >= 2:
                                        game_position = f"{game_fen_parts[0]} {game_fen_parts[1]}"
                                        if game_position == position_pattern:
                                            found_games.append(game_obj)
                                            print(f"DEBUG: Found position match in game: {game_obj.properties.get('white_player')} vs {game_obj.properties.get('black_player')}")
                                            break
                                    if len(found_games) >= limit:
                                        break
                                if len(found_games) >= limit:
                                    break
                
                # Also search final_fen and mid_game_fen for exact and normalized matches
                for fen_to_search in [fen, normalized_search_fen]:
                    if len(found_games) >= limit:
                        break
                        
                    final_fen_result = game_collection.query.fetch_objects(
                        filters=weaviate_query.Filter.by_property("final_fen").equal(fen_to_search),
                        limit=limit - len(found_games)
                    )
                    
                    if final_fen_result and final_fen_result.objects:
                        found_games.extend(final_fen_result.objects)
                        print(f"DEBUG: Found {len(final_fen_result.objects)} games with FEN as final_fen")
                    
                    mid_game_result = game_collection.query.fetch_objects(
                        filters=weaviate_query.Filter.by_property("mid_game_fen").equal(fen_to_search),
                        limit=limit - len(found_games)
                    )
                    
                    if mid_game_result and mid_game_result.objects:
                        found_games.extend(mid_game_result.objects)
                        print(f"DEBUG: Found {len(mid_game_result.objects)} games with FEN as mid_game_fen")
            
            # Process found games
            seen_uuids = set()
            for i, game_obj in enumerate(found_games[:limit]):
                if str(game_obj.uuid) in seen_uuids:
                    continue  # Skip duplicates
                seen_uuids.add(str(game_obj.uuid))
                
                obj_props = game_obj.properties
                
                # Determine match type
                if is_starting_position:
                    match_type = "starting_position"
                elif obj_props.get("final_fen") == fen:
                    match_type = "final_position"
                elif obj_props.get("mid_game_fen") == fen:
                    match_type = "mid_game_position"
                else:
                    match_type = "position_in_game"
                
                all_matching_items.append({
                    "type": "chess_game_search_result",
                    "game_id": str(game_obj.uuid),
                    "uuid": str(game_obj.uuid),
                    "white_player": obj_props.get("white_player"),
                    "black_player": obj_props.get("black_player"),
                    "white_elo": obj_props.get("white_elo"),
                    "black_elo": obj_props.get("black_elo"),
                    "white_fide_id": obj_props.get("white_fide_id"),
                    "black_fide_id": obj_props.get("black_fide_id"),
                    "event": obj_props.get("event"),
                    "site": obj_props.get("site"),
                    "date": obj_props.get("date_utc"),  # Fixed: use date_utc
                    "round": obj_props.get("round"),
                    "eco": obj_props.get("eco"),
                    "opening": obj_props.get("opening"),  # Fixed: use opening instead of opening_name
                    "result": obj_props.get("result"),
                    "pgn_moves": obj_props.get("pgn_moves"),
                    "ply_count": obj_props.get("ply_count"),
                    "source_file": obj_props.get("source_file"),
                    "matched_fen": fen,
                    "fen_match_type": match_type,
                    "source": "chess_game",
                    "score": 20 - (i * 0.1),
                })
                
                if len(all_matching_items) >= limit:
                    break
                    
        except Exception as e:
            print(f"Error searching ChessGame collection: {e}")
            all_matching_items = []

        # === FALLBACK: SEARCH OTHER COLLECTIONS ===
        # Search for lessons/chunks with this FEN (skip if ChessLessonChunk doesn't exist)
        try:
            collection = client.collections.get(etl_config_module.WEAVIATE_CLASS_NAME)
            fen_search_result = collection.query.fetch_objects(
                filters=weaviate_query.Filter.by_property("fen").equal(fen),
                return_properties=["language", "content", "image", "type", "processing_method", 
                                 "source_file", "diagram_analysis", "fen", "book_title", 
                                 "lesson_number", "lesson_title", "content_type"]
            )
            
            if fen_search_result.objects:
                for obj in fen_search_result.objects:
                    obj_props = obj.properties
                    all_matching_items.append({
                        "source": "lesson_chunk",
                        "score": 15,
                        "data": obj_props
                    })
                print(f"Found {len(fen_search_result.objects)} lesson chunks with FEN")
                
        except Exception as e:
            print(f"Error searching lesson chunks: {e}")

        # Search opening book
        opening_matches = query_opening_book_by_fen(etl_config_module.OPENING_BOOK_PATH, fen, k=3)
        for opening_match in opening_matches:
            all_matching_items.append({
                "source": "chess_opening",
                "score": 10,
                "data": opening_match
            })
        
        if opening_matches:
            print(f"Found {len(opening_matches)} opening book matches")

        # # client.close() removed - Weaviate client manages connections automatically  # Removed - newer Weaviate client manages connections automatically

        if not all_matching_items:
            return [{"message": f"No items found with FEN: {fen}"}]

        # Sort by score (higher score is better)
        all_matching_items.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Return unique items and limit the number of results
        final_results = []
        seen_identifiers = set()

        for item in all_matching_items:
            identifier = None
            if item["source"] == "chess_opening":
                identifier = item["data"].get("fen")
            elif item["source"] == "lesson_chunk":
                identifier = item["data"].get("source_file", "") + "_" + item["data"].get("lesson_number", "") + "_" + item["data"].get("content_type", "")
            elif item["source"] == "chess_game":
                identifier = item.get("game_id")
            
            if identifier and identifier not in seen_identifiers:
                if item["source"] == "chess_game":
                    final_results.append(item)
                else:
                    final_results.append(item["data"])
                seen_identifiers.add(identifier)
            elif not identifier:
                if item["source"] == "chess_game":
                    final_results.append(item)
                else:
                    final_results.append(item["data"])

            if len(final_results) >= limit:
                break
        
        return final_results

    except Exception as e:
        print(f"Error in retrieve_by_fen: {e}")
        import traceback
        traceback.print_exc()
        return [{"message": f"Error retrieving FEN: {str(e)}"}]

def retrieve_by_diagram_number(diagram_number: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves lesson chunks that contain a reference to a specific diagram number.
    
    Args:
        diagram_number: The diagram number to search for
        limit: Maximum number of results to return
        
    Returns:
        A list of retrieved chunks
    """
    client = get_weaviate_client()
    if not client:
        return [{"error": "Could not connect to Weaviate database"}]
    
    try:
        # Query for chunks with chunk_id containing the diagram number
        collection = client.collections.get(etl_config_module.WEAVIATE_CLASS_NAME)
        
        # Get all objects (up to a reasonable limit) and filter manually
        all_results = collection.query.fetch_objects(limit=100)
        
        if not all_results.objects:
            return [{"message": f"No chunks found in database."}]
        
        # Filter for chunks that match our diagram number
        matching_chunks = []
        
        for obj in all_results.objects:
            obj_props = obj.properties
            source_file = obj_props.get("source_file", "")  # Use source_file instead of chunk_id
            content = obj_props.get("content", "").lower()  # Use content instead of text
            
            # First priority: Check for exact match in source_file (images often have diagram references)
            if f"diagram_doc_img{diagram_number}" in source_file:
                matching_chunks.append(obj_props)
                continue
            
            # Second priority: Check for diagram number in content
            if (f"диаграмма {diagram_number}" in content or 
                f"диаграммa {diagram_number}" in content or # Cyrillic 'a'
                f"диаграмм {diagram_number}" in content or
                f"диаграммы {diagram_number}" in content or
                f"diagram {diagram_number}" in content or
                f"#{diagram_number}" in content or
                f"№{diagram_number}" in content):
                matching_chunks.append(obj_props)
                continue
            
            # Third priority: Check if this is a task with the diagram number
            if obj_props.get("type") in ["task", "general_task"]:
                if content.strip() == str(diagram_number): # Task content is just the number
                    matching_chunks.append(obj_props)
                    continue
                if obj_props.get("diagram_number_reference") == diagram_number:
                    matching_chunks.append(obj_props)
                    continue
        
        if not matching_chunks:
            return [{"message": f"No chunks found with diagram number: {diagram_number}"}]
        
        print(f"Found {len(matching_chunks)} chunks matching diagram number {diagram_number}")
        return matching_chunks[:limit]
        
    except Exception as e:
        return [{"error": f"Error querying Weaviate for diagrams: {str(e)}"}]
    finally:
        if client:
            pass  # # client.close() removed - Weaviate client manages connections automatically removed - newer Weaviate client manages connections automatically

def retrieve_semantic(query: str, limit: int = 25, context_fen: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Performs a semantic search. If a FEN is in the query or provided as context_fen, 
    gets live Stockfish analysis for it. Then searches Weaviate for relevant lesson chunks and chess openings.
    """
    all_relevant_objects = []
    query_terms = query.lower().split()

    # Determine FEN to analyze: prioritize context_fen, then FEN in query.
    fen_to_analyze_live = context_fen
    if not fen_to_analyze_live:
        fen_to_analyze_live = extract_fen_from_query(query)

    # 1. Live Stockfish analysis if a FEN is identified for analysis
    if fen_to_analyze_live:
        print(f"FEN identified for live analysis: {fen_to_analyze_live}. Getting Stockfish analysis.")
        if not etl_config_module.STOCKFISH_PATH:
            print("STOCKFISH_PATH not set. Skipping live analysis.")
        else:
            try:
                # Assuming analyze_fen_with_stockfish returns a dict as per its usage elsewhere
                # Example: {'best_move': 'e4', 'evaluation': '+0.5', 'top_lines': [...]}
                # The existing code expected different keys, so I'll adapt to a more generic structure for the analysis dictionary.
                stockfish_analysis_result = analyze_fen_with_stockfish(fen_to_analyze_live, multipv=3, time_limit=1.0) # Use multipv
                
                if stockfish_analysis_result: # Check if analysis returned something meaningful
                    # Construct a text summary from the analysis lines
                    summary_parts = [f"Live Stockfish analysis for FEN '{fen_to_analyze_live}':"]
                    for line_info in stockfish_analysis_result: # Iterate over list of lines
                        summary_parts.append(f"  Line {line_info.get('line_number', '?')}: {line_info.get('pv_san', 'N/A')} (Eval: {line_info.get('evaluation_string', 'N/A')})")
                    text_summary_val = "\n".join(summary_parts)
                    
                    all_relevant_objects.append({
                        "type": "live_stockfish_analysis",
                        "query_fen": fen_to_analyze_live,
                        "analysis_data": stockfish_analysis_result, # Store the raw analysis lines
                        "text_summary": text_summary_val,
                        "source": "Stockfish Engine (Live)",
                        "score": 20  # High score for direct analysis
                    })
                else:
                    print(f"Stockfish analysis for {fen_to_analyze_live} returned no data.")

            except Exception as e:
                print(f"Error getting live Stockfish analysis for FEN '{fen_to_analyze_live}': {e}")
                all_relevant_objects.append({
                    "type": "error_stockfish_analysis",
                    "query_fen": fen_to_analyze_live,
                    "error_message": str(e),
                    "source": "Stockfish Engine (Live)",
                    "score": 0
                })
    else:
        print("No FEN identified in query or context for live Stockfish analysis.")

    # 2. Weaviate search for lesson chunks and openings
    client = get_weaviate_client()
    if not client:
        if not all_relevant_objects: # Only return error if no Stockfish results
            return [{"error": "Could not connect to Weaviate database"}]
        print("Could not connect to Weaviate for semantic search. Proceeding with Stockfish results if any.")
    else:
        try:
            # 2a. Query ChessLessonChunk
            try:
                lesson_collection = client.collections.get(etl_config_module.WEAVIATE_CLASS_NAME)
                # Fetch a generous amount for local filtering, default is 100
                lesson_results = lesson_collection.query.fetch_objects(limit=100) 
                if lesson_results and lesson_results.objects:
                    for obj in lesson_results.objects:
                        obj_props = obj.properties
                        score = 0
                        text_content = obj_props.get("content", "").lower()
                        
                        for term in query_terms:
                            if term in text_content: score += 3
                        if obj_props.get("book_title") and any(term in obj_props["book_title"].lower() for term in query_terms): score += 2
                        if obj_props.get("lesson_title") and any(term in obj_props["lesson_title"].lower() for term in query_terms): score += 2
                        if obj_props.get("lesson_number") and any(term.isdigit() and term == str(obj_props["lesson_number"]) for term in query_terms): score += 2 # str comparison
                        if obj_props.get("source_file") and "diagram" in query.lower() and "diagram" in obj_props.get("source_file", "").lower(): score += 1 # Fixed: use source_file instead of chunk_id

                        if obj_props.get("fen"):
                            if "fen" in query.lower(): score += 5
                            if fen_to_analyze_live and obj_props.get("fen", "").strip() == fen_to_analyze_live: score += 10 # Boost if FEN matches query's FEN
                        
                        if score > 0:
                            item = obj_props.copy()
                            item["source"] = etl_config_module.WEAVIATE_CLASS_NAME
                            item["score"] = score
                            all_relevant_objects.append(item)
            except Exception as e:
                print(f"Error querying {etl_config_module.WEAVIATE_CLASS_NAME}: {e}")
                if not all_relevant_objects: all_relevant_objects.append({"error": f"Error querying Weaviate class {etl_config_module.WEAVIATE_CLASS_NAME}: {e}"})

            # 2b. Query ChessOpening
            try:
                opening_collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
                opening_results = opening_collection.query.fetch_objects(limit=100) # Fetch more for filtering
                if opening_results and opening_results.objects:
                    for obj in opening_results.objects:
                        obj_props = obj.properties
                        score = 0
                        name_lower = obj_props.get("opening", "").lower()  # Fixed: ChessGame uses 'opening'
                        eco_lower = obj_props.get("eco", "").lower()  # Fixed: ChessGame uses 'eco'
                        san_lower = obj_props.get("pgn_moves", "").lower()  # Fixed: ChessGame actually uses 'pgn_moves'

                        for term in query_terms:
                            if term in name_lower: score += 5
                            if term in eco_lower: score += 3
                            if term in san_lower: score += 2
                        
                        # Boost if game's FEN matches extracted FEN from query
                        if fen_to_analyze_live:
                            # Check final_fen (end of game)
                            if obj_props.get("final_fen", "").strip() == fen_to_analyze_live:
                                score += 15
                            # Check mid_game_fen (middle of game)
                            elif obj_props.get("mid_game_fen", "").strip() == fen_to_analyze_live:
                                score += 12
                            # Check if FEN appears anywhere in the game (all_ply_fens)
                            elif fen_to_analyze_live in obj_props.get("all_ply_fens", []):
                                score += 10

                        if score > 0:
                            item_data = {
                                "type": "chess_game",  # Fixed: this is actually a chess game, not opening
                                "name": obj_props.get("opening"),  # Fixed: ChessGame uses 'opening'
                                "eco": obj_props.get("eco"),  # Fixed: ChessGame uses 'eco'
                                "fen": obj_props.get("final_fen"),  # Fixed: ChessGame uses 'final_fen'
                                "mid_game_fen": obj_props.get("mid_game_fen"),  # Fixed: ChessGame property
                                "pgn_moves": obj_props.get("pgn_moves"),  # Fixed: ChessGame uses 'pgn_moves'
                                "moves": obj_props.get("moves"),  # Fixed: ChessGame uses 'moves'
                                "white_player": obj_props.get("white_player"),  # Add game info
                                "black_player": obj_props.get("black_player"),  # Add game info
                                "event": obj_props.get("event"),  # Add game info
                                "result": obj_props.get("result"),  # Add game info
                                "text_summary": f"Game: {obj_props.get('white_player')} vs {obj_props.get('black_player')} - {obj_props.get('opening')} (ECO: {obj_props.get('eco')})"
                            }
                            all_relevant_objects.append({
                                "data": item_data, # Keep structure consistent if some items have 'data' sub-dict
                                "source": CHESS_OPENING_CLASS_NAME,
                                "score": score
                            })
            except Exception as e:
                print(f"Error querying {CHESS_OPENING_CLASS_NAME}: {e}")
                if not all_relevant_objects: all_relevant_objects.append({"error": f"Error querying Weaviate class {CHESS_OPENING_CLASS_NAME}: {e}"})

            # 3. Query ChessGame (for actual game records with UUIDs)
            try:
                import weaviate.classes.query as weaviate_query
                
                game_collection = client.collections.get("ChessGame")
                
                # Build proper filters for player names to avoid unrelated games
                game_filters = []
                player_terms = []
                
                # Identify potential player names in query terms
                for term in query_terms:
                    # Check if term could be a player name (longer than 2 chars, not common chess terms)
                    if len(term) > 2 and term not in ['game', 'chess', 'move', 'opening', 'white', 'black', 'win', 'loss', 'draw']:
                        player_terms.append(term)
                
                # If we have potential player names, use proper filters
                if player_terms:
                    player_filters = []
                    for player_term in player_terms:
                        player_filters.extend([
                            weaviate_query.Filter.by_property("white_player").like(f"*{player_term}*"),
                            weaviate_query.Filter.by_property("black_player").like(f"*{player_term}*")
                        ])
                    
                    # Use OR for player filters (match any player name)
                    if player_filters:
                        game_filters.append(weaviate_query.Filter.any_of(player_filters))
                
                # Apply filters if we have any, otherwise do a limited fetch
                final_filter = None
                if game_filters:
                    final_filter = weaviate_query.Filter.all_of(game_filters) if len(game_filters) > 1 else game_filters[0]
                
                # Query with proper filters
                game_results = game_collection.query.fetch_objects(
                    filters=final_filter,
                    limit=20  # Reduced limit since we're using proper filters
                )
                
                if game_results and game_results.objects:
                    for obj in game_results.objects:
                        obj_props = obj.properties
                        score = 0
                        name_lower = obj_props.get("opening", "").lower()  # Fixed: ChessGame uses 'opening'
                        eco_lower = obj_props.get("eco", "").lower()
                        san_lower = obj_props.get("pgn_moves", "").lower()  # Fixed: ChessGame uses 'pgn_moves'
                        white_player_lower = obj_props.get("white_player", "").lower()
                        black_player_lower = obj_props.get("black_player", "").lower()

                        # Score based on query terms
                        for term in query_terms:
                            if term in name_lower: score += 5
                            if term in eco_lower: score += 3
                            if term in san_lower: score += 2
                            # Higher score for player name matches
                            if term in white_player_lower: score += 10
                            if term in black_player_lower: score += 10
                        
                        # Boost if game's FEN matches extracted FEN from query
                        if fen_to_analyze_live:
                            # Check final_fen (end of game)
                            if obj_props.get("final_fen", "").strip() == fen_to_analyze_live:
                                score += 15
                            # Check mid_game_fen (middle of game)
                            elif obj_props.get("mid_game_fen", "").strip() == fen_to_analyze_live:
                                score += 12
                            # Check if FEN appears anywhere in the game (all_ply_fens)
                            elif fen_to_analyze_live in obj_props.get("all_ply_fens", []):
                                score += 10
                        # Fixed: Now using correct ChessGame schema properties

                        # Only include games with meaningful scores
                        if score > 0:
                            item_data = {
                                "type": "chess_game_search_result",  # Changed to match game search agent
                                "game_id": str(obj.uuid),  # Add the UUID that users need!
                                "uuid": str(obj.uuid),  # Also include as uuid for compatibility
                                "opening": obj_props.get("opening"),  # Fixed: ChessGame uses 'opening'
                                "eco": obj_props.get("eco"),
                                "ending_fen": obj_props.get("final_fen"),  # Fixed: ChessGame uses 'final_fen'
                                "mid_game_fen": obj_props.get("mid_game_fen"),  # Fixed: ChessGame property
                                "pgn_moves": obj_props.get("pgn_moves"),  # Fixed: ChessGame uses 'pgn_moves'
                                "moves": obj_props.get("moves"),  # Fixed: ChessGame uses 'moves'
                                "white_player": obj_props.get("white_player"),  # Add player info
                                "black_player": obj_props.get("black_player"),  # Add player info
                                "event": obj_props.get("event"),  # Add event info
                                "result": obj_props.get("result"),  # Add result info
                                "text_summary": f"Game: {obj_props.get('white_player')} vs {obj_props.get('black_player')} - {obj_props.get('opening')} (ECO: {obj_props.get('eco')})"
                            }
                            # For chess_game_search_result, return flat structure like retrieve_by_fen
                            item_data["source"] = "ChessGame"
                            item_data["score"] = score
                            all_relevant_objects.append(item_data)
            except Exception as e:
                print(f"Error querying ChessGame: {e}")
                if not all_relevant_objects: all_relevant_objects.append({"error": f"Error querying Weaviate class ChessGame: {e}"})
        finally:
            if client:
                pass  # # client.close() removed - Weaviate client manages connections automatically removed - newer Weaviate client manages connections automatically

    # 3. Sort, deduplicate, and limit results
    all_relevant_objects.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    final_results = []
    seen_identifiers = set() # Using a simple identifier for deduplication

    for item in all_relevant_objects:
        identifier = None
        if item.get("type") == "live_stockfish_analysis":
            identifier = item.get("query_fen") # FEN is a good unique ID here
        elif item.get("type") == "chess_game_search_result":
            identifier = item.get("game_id") or item.get("uuid") # Use game UUID as identifier
        elif item.get("source") == CHESS_OPENING_CLASS_NAME and item.get("data"):
            identifier = item["data"].get("fen") # FEN of the opening
        elif item.get("source") == etl_config_module.WEAVIATE_CLASS_NAME:
            # For lesson chunks, use source_file + lesson_number + content_type for identification, or content hash if not available
            identifier = item.get("source_file", "") + "_" + str(item.get("lesson_number", "")) + "_" + item.get("content_type", "") or hash(item.get("content", "")[:100])
        elif item.get("error"): # Always include error messages
            final_results.append(item)
            if len(final_results) >= limit: break
            continue
        
        if identifier:
            if identifier not in seen_identifiers:
                final_results.append(item)
                seen_identifiers.add(identifier)
        else: # Fallback for items without clear identifiers (should be rare)
             if item not in final_results : final_results.append(item)

        if len(final_results) >= limit:
            break
            
    if not final_results: # If still no results after all attempts
        return [{"message": f"No relevant information found for: {query}"}]
        
    return final_results

def retrieve_diagrams_for_lesson(lesson_title: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves all diagram image chunks associated with a specific lesson title.
    
    Args:
        lesson_title: The exact title of the lesson to retrieve diagrams for.
        limit: Maximum number of diagram chunks to return.
        
    Returns:
        A list of diagram chunks, or an error/message.
    """
    client = get_weaviate_client()
    if not client:
        return [{"error": "Could not connect to Weaviate database"}]

    try:
        lesson_collection = client.collections.get(etl_config_module.WEAVIATE_CLASS_NAME)
        
        # Fetch objects matching the lesson_title and type 'diagram_image_chunk'
        # This assumes 'type' and 'lesson_title' are top-level properties in your Weaviate schema for these chunks.
        
        # Broad fetch then filter, as direct filtering on multiple exact properties might be tricky
        # or less efficient depending on Weaviate version/setup without proper indexing for filters.
        all_lesson_items = lesson_collection.query.fetch_objects(limit=200) # Fetch more to filter locally
        
        diagram_chunks = []
        if all_lesson_items and all_lesson_items.objects:
            for obj in all_lesson_items.objects:
                props = obj.properties
                if props.get("lesson_title", "").strip() == lesson_title.strip() and \
                   props.get("type") == "diagram_image_chunk":
                    diagram_chunks.append(props)
        
        if not diagram_chunks:
            return [{"message": f"No diagrams found for lesson: {lesson_title}"}]
            
        # Sort by chunk_id or diagram_number_reference if available, to maintain order
        diagram_chunks.sort(key=lambda x: (
            x.get("diagram_number_reference", float('inf')), 
            x.get("chunk_id", "")
        ))
        
        return diagram_chunks[:limit]

    except Exception as e:
        return [{"error": f"Error retrieving diagrams for lesson '{lesson_title}': {str(e)}"}]
    finally:
        if client:
            pass  # # client.close() removed - Weaviate client manages connections automatically removed - newer Weaviate client manages connections automatically

class RetrieverAgent:
    def __init__(self, 
                 client: WeaviateSDKClient, 
                 opening_book_path: str):
        self.client = client
        self.opening_book_path = opening_book_path
        
        # Initialize enhanced retriever
        self.enhanced_retriever = EnhancedRetriever(client, self)
        
        # Initialize advanced RAG retriever (Crawl4AI-inspired enhancements)
        try:
            self.advanced_rag_retriever = create_advanced_rag_retriever(client, self.enhanced_retriever)
            logger.info("Advanced RAG retriever initialized successfully")
        except Exception as e:
            logger.warning(f"Advanced RAG retriever initialization failed: {e}")
            self.advanced_rag_retriever = None
        
        logger.info(f"RetrieverAgent initialized. Weaviate client: {type(client)}, Opening book: {opening_book_path}")
        logger.info("Enhanced retrieval capabilities enabled")
        if self.advanced_rag_retriever:
            logger.info("Advanced RAG capabilities enabled (Hybrid Search + Reranking)")
        else:
            logger.info("Advanced RAG capabilities disabled - using enhanced retriever only")

    def _determine_collection_for_query(self, query: str) -> str:
        """Determine which Weaviate collection to search based on query content"""
        query_lower = query.lower()
        
        # Russian education keywords that indicate lesson content
        education_keywords = [
            'урок', 'lesson', 'шах', 'мат', 'checkmate', 'check', 
            'документ', 'document', 'книг', 'book', 'обучен', 'education',
            'урок 2', 'lesson 2', 'russian', 'русский', 'защит', 'defense',
            'тактик', 'tactics', 'стратег', 'strategy', 'диаграмм', 'diagram'
        ]
        
        # Check if query contains education-related keywords
        if any(keyword in query_lower for keyword in education_keywords):
            logger.info(f"🎓 Query '{query}' detected as education content - using ChessLessonChunk")
            return "ChessLessonChunk"
        else:
            logger.info(f"🎮 Query '{query}' detected as game content - using ChessGame")
            return "ChessGame"
    
    @performance_monitor.timer('enhanced_retrieve')
    def enhanced_retrieve(self, query: str, metadata: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Enhanced retrieval with contextual filtering using the unified filter system
        """
        try:
            # Handle None metadata by providing a default empty dictionary
            if metadata is None:
                metadata = {}
                logger.warning("enhanced_retrieve called with None metadata, using empty dict")
            
            # Initialize unified filter system
            filter_system = UnifiedFilterSystem()
            
            # Parse filters from query
            current_fen = metadata.get("fen_for_analysis") or metadata.get("fen_for_game_search")
            filter_criteria = filter_system.parse_query_filters(query, current_fen)
            
            logger.info(f"Enhanced retrieve - Filter criteria: {filter_criteria}")
            
            # Use existing retrieval logic but add filtering support
            primary_filter = filter_criteria.get_primary_filter_type()
            if primary_filter and hasattr(primary_filter, 'name'):
                primary_filter_name = primary_filter.name
                logger.info(f"Primary filter type: {primary_filter_name}")
                
                # Handle ELO filtering specifically
                if primary_filter_name == "ELO_RANGE":
                    return self._retrieve_with_elo_filters(query, filter_criteria, metadata)
                elif primary_filter_name == "PLAYER_NAME":
                    return self._retrieve_with_player_filters(query, filter_criteria, metadata)
                elif primary_filter_name == "FEN_POSITION":
                    return self._retrieve_with_fen_filters(query, filter_criteria, metadata)
            
            # Fallback to standard retrieve
            return self.retrieve(query, metadata)
            
        except Exception as e:
            logger.error(f"Error in enhanced_retrieve: {e}", exc_info=True)
            return self.retrieve(query, metadata)
    
    def _retrieve_with_elo_filters(self, query: str, criteria, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve games with ELO filtering"""
        try:
            import weaviate.classes.query as weaviate_query
            
            # Get the game collection
            game_collection = self.client.collections.get("ChessGame")
            
            # Build ELO filters using the correct Weaviate v4 syntax
            elo_conditions = []
            
            if criteria.white_elo_min:
                elo_conditions.append(
                    weaviate_query.Filter.by_property("white_elo").greater_or_equal(criteria.white_elo_min)
                )
            if criteria.white_elo_max:
                elo_conditions.append(
                    weaviate_query.Filter.by_property("white_elo").less_or_equal(criteria.white_elo_max)
                )
            if criteria.black_elo_min:
                elo_conditions.append(
                    weaviate_query.Filter.by_property("black_elo").greater_or_equal(criteria.black_elo_min)
                )
            if criteria.black_elo_max:
                elo_conditions.append(
                    weaviate_query.Filter.by_property("black_elo").less_or_equal(criteria.black_elo_max)
                )
            
            # Combine filters if multiple exist
            if len(elo_conditions) > 1:
                combined_filter = weaviate_query.Filter.all_of(elo_conditions)
            elif len(elo_conditions) == 1:
                combined_filter = elo_conditions[0]
            else:
                combined_filter = None
            
            # Query with filters
            if combined_filter:
                result = game_collection.query.fetch_objects(
                    where=combined_filter,
                    limit=criteria.limit,
                    return_properties=["white_player", "black_player", "white_elo", "black_elo", 
                                     "event", "date_utc", "result", "eco", "opening", "pgn_moves"]
                )
            else:
                result = game_collection.query.fetch_objects(limit=criteria.limit)
            
            games = []
            if result and result.objects:
                for obj in result.objects:
                    game_data = obj.properties
                    game_data['uuid'] = str(obj.uuid)
                    games.append(game_data)
            
            logger.info(f"Found {len(games)} games with ELO filters: white_elo>={criteria.white_elo_min}, black_elo>={criteria.black_elo_min}")
            
            return {
                "retrieved_items": games,
                "query": query,
                "metadata": {
                    "filter_type": "elo_range",
                    "white_elo_min": criteria.white_elo_min,
                    "black_elo_min": criteria.black_elo_min,
                    "total_results": len(games)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in ELO filtering: {e}", exc_info=True)
            return {"retrieved_items": [], "query": query, "error": str(e)}
    
    def _retrieve_with_player_filters(self, query: str, criteria, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve games with player filtering"""
        # Use the existing retrieve_by_player method but return in the correct format
        player_name = criteria.any_player or criteria.white_player or criteria.black_player
        games = self.retrieve_by_player(player_name, criteria.limit)
        
        return {
            "retrieved_items": games,
            "query": query,
            "metadata": {
                "filter_type": "player_search",
                "player_name": player_name,
                "total_results": len(games)
            }
        }
    
    def _retrieve_with_fen_filters(self, query: str, criteria, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve games with FEN filtering"""
        # Use the existing retrieve_by_fen method but return in the correct format
        fen_result = self.retrieve_by_fen(criteria.fen_position, criteria.limit)
        
        # The retrieve_by_fen returns a dict with 'retrieved_chunks' and 'stockfish_analysis'
        # We need to transform this to match the expected format
        retrieved_items = fen_result.get('retrieved_chunks', [])
        
        return {
            "retrieved_items": retrieved_items,
            "query": query,
            "metadata": {
                "filter_type": "fen_search",
                "fen_position": criteria.fen_position,
                "total_results": len(retrieved_items)
            },
            "stockfish_analysis": fen_result.get('stockfish_analysis', [])
        }

    def retrieve_by_fen(self, fen: str, limit: int = 3) -> Dict[str, Any]:
        """
        Retrieves documents by FEN using the module-level retrieve_by_fen function.
        """
        logger.info(f"RetrieverAgent.retrieve_by_fen called with FEN: {fen}, limit: {limit}")
        
        # Call the module-level retrieve_by_fen function
        retrieved_chunks = retrieve_by_fen(fen=fen, limit=limit)
        
        # Get Stockfish analysis for the FEN
        stockfish_analysis_results = None
        if is_fen_like(fen):
            logger.info(f"Getting Stockfish analysis for FEN: {fen}")
            stockfish_analysis_results = analyze_fen_with_stockfish(fen, time_limit=1.0, multipv=3)
            if stockfish_analysis_results:
                logger.info(f"Stockfish analysis for FEN '{fen}' returned {len(stockfish_analysis_results)} lines.")
            else:
                logger.warning(f"Stockfish analysis for FEN '{fen}' returned no results or failed.")
        
        # Return the result in the expected format
        result = {
            "retrieved_chunks": retrieved_chunks,
            "stockfish_analysis": stockfish_analysis_results if stockfish_analysis_results else []
        }
        
        logger.info(f"RetrieverAgent.retrieve_by_fen returning {len(retrieved_chunks)} chunks")
        return result

    def retrieve_by_player(self, player_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves chess games by player name (searches both white and black players).
        
        Args:
            player_name: The player name to search for
            limit: Maximum number of games to return
            
        Returns:
            List of game dictionaries containing player games
        """
        logger.info(f"RetrieverAgent.retrieve_by_player called with player: {player_name}, limit: {limit}")
        
        if not player_name or not player_name.strip():
            logger.warning("Empty player name provided")
            return []
        
        player_name = player_name.strip()
        found_games = []
        
        try:
            # Get the ChessGame collection
            game_collection = self.client.collections.get("ChessGame")
            
            # Search for player in both white_player and black_player fields using OR logic
            import weaviate.classes.query as weaviate_query
            
            # Create filters for white and black player searches
            white_player_filter = weaviate_query.Filter.by_property("white_player").like(f"*{player_name}*")
            black_player_filter = weaviate_query.Filter.by_property("black_player").like(f"*{player_name}*")
            
            # Combine with OR logic
            player_filter = weaviate_query.Filter.any_of([white_player_filter, black_player_filter])
            
            # Execute the query - fix: use 'where' not 'filters'
            results = game_collection.query.fetch_objects(
                where=player_filter,
                limit=limit,
                return_properties=[
                    "white_player", "black_player", "event", "site", "round", "date_utc", 
                    "result", "eco", "opening_name", "ply_count", "final_fen", "mid_game_fen",
                    "pgn_moves", "source_file", "white_elo", "black_elo", "event_date",
                    "white_title", "black_title", "white_fide_id", "black_fide_id"
                ]
            )
            
            if results and results.objects:
                for game_obj in results.objects:
                    game_data = dict(game_obj.properties)
                    game_data["uuid"] = str(game_obj.uuid)
                    game_data["type"] = "chess_game"
                    game_data["source"] = "player_search"
                    
                    # Add computed fields
                    if game_data.get("white_elo") and game_data.get("black_elo"):
                        try:
                            white_elo = int(game_data["white_elo"])
                            black_elo = int(game_data["black_elo"])
                            game_data["average_elo"] = (white_elo + black_elo) / 2
                        except (ValueError, TypeError):
                            pass
                    
                    found_games.append(game_data)
                
                logger.info(f"Found {len(found_games)} games for player '{player_name}'")
            else:
                logger.info(f"No games found for player '{player_name}'")
                
        except Exception as e:
            logger.error(f"Error searching for player '{player_name}': {e}")
            import traceback
            traceback.print_exc()
        
        return found_games

    def retrieve_semantic(self, 
                          query: str, 
                          k: int = 3, 
                          alpha: float = 0.5, 
                          vector: List[float] = None,
                          properties: List[str] = None,
                          class_name: str = None, # Default to ChessGame (only collection we have)
                          context_fen: str = None, # Added context_fen
                          analyze_board: bool = True # Added flag to control Stockfish analysis
                          ) -> Dict[str, Any]:
        """
        Performs semantic search, optionally with Stockfish analysis if context_fen is provided.
        """
        logger.info(f"RetrieverAgent: Semantic search for query: '{query}', k={k}, alpha={alpha}, class_name={class_name}, context_fen={context_fen}")
        
        
        # ENHANCED: Determine collection based on query content
        if class_name is None:
            # Analyze query to determine appropriate collection
            query_lower = query.lower()
            russian_education_keywords = [
                'урок', 'lesson', 'шах', 'мат', 'checkmate', 'check', 
                'документ', 'document', 'книг', 'book', 'обучен', 'education',
                'урок 2', 'lesson 2', 'russian', 'русский'
            ]
            
            # Check if query is about Russian education content
            if any(keyword in query_lower for keyword in russian_education_keywords):
                class_name = "ChessLessonChunk"
                logger.info(f"🎓 Detected education query, using ChessLessonChunk collection")
            else:
                class_name = "ChessGame"
                logger.info(f"🎮 Using default ChessGame collection")
        
        # Use direct fetch approach instead of search_weaviate to avoid vectorization issues
        retrieved_chunks = []
        
        try:
            if class_name == "ChessLessonChunk":
                # Use direct fetch for ChessLessonChunk since semantic search fails
                logger.info(f"Using direct fetch for ChessLessonChunk collection")
                collection = self.client.collections.get(class_name)
                results = collection.query.fetch_objects(limit=100)
                
                if results and results.objects:
                    query_terms = query.lower().split()
                    for obj in results.objects:
                        obj_props = obj.properties
                        score = 0
                        text_content = obj_props.get("content", "").lower()
                        
                        # Score based on query terms
                        for term in query_terms:
                            if term in text_content: score += 3
                        if obj_props.get("book_title") and any(term in obj_props["book_title"].lower() for term in query_terms): score += 2
                        if obj_props.get("lesson_title") and any(term in obj_props["lesson_title"].lower() for term in query_terms): score += 2
                        if obj_props.get("lesson_number") and any(term.isdigit() and term == str(obj_props["lesson_number"]) for term in query_terms): score += 2
                        if obj_props.get("source_file") and "diagram" in query.lower() and "diagram" in obj_props.get("source_file", "").lower(): score += 1

                        if obj_props.get("fen"):
                            if "fen" in query.lower(): score += 5
                            if context_fen and obj_props.get("fen", "").strip() == context_fen: score += 10
                        
                        if score > 0:
                            item = obj_props.copy()
                            item["source"] = class_name
                            item["score"] = score
                            retrieved_chunks.append(item)
                    
                    # Sort by score and limit results
                    retrieved_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
                    retrieved_chunks = retrieved_chunks[:k]
                    
                logger.info(f"Direct fetch found {len(retrieved_chunks)} relevant chunks")
            else:
                # For other collections, try search_weaviate but fall back to direct fetch if it fails
                try:
                    retrieved_chunks = search_weaviate(
                        client=self.client,
                        query_text=query,
                        collection_name=class_name,
                        top_k=k,
                        fen=context_fen,
                        properties=properties
                    )
                    logger.info(f"search_weaviate found {len(retrieved_chunks)} chunks")
                except Exception as e:
                    logger.warning(f"search_weaviate failed for {class_name}: {e}, falling back to direct fetch")
                    # Fallback to direct fetch
                    collection = self.client.collections.get(class_name)
                    results = collection.query.fetch_objects(limit=100)
                    retrieved_chunks = []
                    if results and results.objects:
                        for obj in results.objects[:k]:
                            item = obj.properties.copy()
                            item["source"] = class_name
                            item["score"] = 1  # Default score
                            retrieved_chunks.append(item)
                    logger.info(f"Direct fetch fallback found {len(retrieved_chunks)} chunks")
                    
        except Exception as e:
            logger.error(f"Error in retrieve_semantic: {e}")
            retrieved_chunks = []

        stockfish_analysis_results = None
        if analyze_board and context_fen and is_fen_like(context_fen):
            logger.info(f"Context FEN '{context_fen}' provided and is valid, performing Stockfish analysis.")
            # Use the imported analyze_fen_with_stockfish directly
            # Time limit can be adjusted. 1.0s is a reasonable default.
            stockfish_analysis_results = analyze_fen_with_stockfish(context_fen, time_limit=1.0, multipv=3)
            if stockfish_analysis_results:
                logger.info(f"Stockfish analysis for context FEN '{context_fen}' returned {len(stockfish_analysis_results)} lines.")
            else:
                logger.warning(f"Stockfish analysis for context FEN '{context_fen}' returned no results or failed.")
        elif analyze_board and context_fen and not is_fen_like(context_fen):
            logger.warning(f"Context FEN '{context_fen}' provided but is invalid. Skipping Stockfish analysis.")
        elif analyze_board and not context_fen:
            logger.info("No context FEN provided for semantic search, skipping Stockfish analysis.")


        return {
            "retrieved_chunks": retrieved_chunks,
            "stockfish_analysis": stockfish_analysis_results if stockfish_analysis_results else []
        }

    def retrieve(self, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        query_type = metadata.get("query_type", "general_query")
        fen_for_analysis = metadata.get("fen_for_analysis")
        k_results = metadata.get("k_results", etl_config_module.RETRIEVER_TOP_K)
                # ENHANCED: Determine target class based on query content
        default_class = self._determine_collection_for_query(query)
        target_class_name = metadata.get("target_class_name", default_class)
        game_filters = metadata.get("game_filters", {})

        logger.info(f"RetrieverAgent received query: '{query}', type: {query_type}, FEN: {fen_for_analysis}, k: {k_results}, class: {target_class_name}")

        # Handle game_search queries using the game search agent
        if query_type == "game_search":
            logger.info(f"Game search query detected. FEN: {fen_for_analysis}, Filters: {game_filters}")
            try:
                # Use the game search agent for all game searches (with or without filters)
                game_results = find_games_by_criteria(
                    filters=game_filters if game_filters else {},  # Use empty dict if no filters
                    fen_to_match=fen_for_analysis,
                    limit=k_results
                )
                
                # Get Stockfish analysis if FEN is provided
                stockfish_analysis_results = []
                if fen_for_analysis and is_fen_like(fen_for_analysis):
                    logger.info(f"Getting Stockfish analysis for FEN: {fen_for_analysis}")
                    stockfish_analysis_results = analyze_fen_with_stockfish(fen_for_analysis, time_limit=1.0, multipv=3)
                    if stockfish_analysis_results:
                        logger.info(f"Stockfish analysis for FEN '{fen_for_analysis}' returned {len(stockfish_analysis_results)} lines.")
                
                logger.info(f"Game search agent returned {len(game_results)} results")
                return {
                    "retrieved_chunks": game_results,
                    "stockfish_analysis": stockfish_analysis_results,
                    "query_type": query_type
                }
            except Exception as e:
                logger.error(f"Error in game search: {e}")
                # Fall back to the original logic if game search fails
                
        if query_type in ["opening_lookup"] and fen_for_analysis:
            logger.info(f"Dispatching to retrieve_by_fen for {query_type} with FEN: {fen_for_analysis}")
            fen_result = self.retrieve_by_fen(fen=fen_for_analysis, k=k_results)
            
            # Check if FEN search found meaningful results
            retrieved_chunks = fen_result.get("retrieved_chunks", [])
            has_meaningful_results = False
            
            # For game_search queries, only chess games are meaningful results
            if query_type == "game_search":
                for chunk in retrieved_chunks:
                    if not isinstance(chunk, dict):
                        continue
                    # For game search, only chess_game_search_result types are meaningful
                    if chunk.get("type") == "chess_game_search_result":
                        has_meaningful_results = True
                        break
            else:
                # For other query types, use the original logic
                for chunk in retrieved_chunks:
                    if not isinstance(chunk, dict):
                        continue
                    # Check if it's an error or "no items found" message
                    if chunk.get("error") or chunk.get("message"):
                        continue
                    # If we have actual data, it's meaningful
                    if chunk.get("data") or chunk.get("fen") or chunk.get("text"):
                        has_meaningful_results = True
                        break
            
            # If FEN search didn't find meaningful results, fall back to semantic search
            if not has_meaningful_results:
                logger.info(f"FEN search for '{fen_for_analysis}' found no meaningful results. Falling back to semantic search.")
                # Create a more specific query for semantic search
                semantic_query = f"{query} position analysis opening theory"
                if fen_for_analysis:
                    semantic_query += f" FEN: {fen_for_analysis}"
                
                # For game_search queries, search ChessGame collection instead of default ChessLessonChunk
                fallback_class_name = "ChessGame" if query_type == "game_search" else target_class_name
                logger.info(f"Using fallback collection: {fallback_class_name} for query_type: {query_type}")
                
                # Set appropriate properties for each collection type
                if fallback_class_name == "ChessGame":
                    properties = ["event", "site", "date_utc", "round", "white_player", "black_player", "result",
                                "white_elo", "black_elo", "eco", "opening", "ply_count", "pgn_moves", 
                                "final_fen", "mid_game_fen", "source_file", "all_ply_fens"]
                else:
                    properties = None  # Use default properties for other collections
                
                semantic_result = self.retrieve_semantic(
                    query=semantic_query,
                    k=k_results,
                    context_fen=fen_for_analysis,
                    analyze_board=True,
                    class_name=fallback_class_name,
                    properties=properties
                )
                
                # Combine the results, keeping Stockfish analysis from FEN search
                # PRESERVE the original query_type even when falling back to semantic search
                combined_result = {
                    "retrieved_chunks": semantic_result.get("retrieved_chunks", []),
                    "stockfish_analysis": fen_result.get("stockfish_analysis", []),
                    "query_type": query_type,  # Preserve original query type
                    "fallback_used": True  # Indicate that fallback was used
                }
                
                logger.info(f"Semantic fallback found {len(combined_result['retrieved_chunks'])} chunks")
                return combined_result
            else:
                logger.info(f"FEN search found meaningful results, returning them")
                # Add query_type to the FEN result
                fen_result["query_type"] = query_type
                logger.info(f"DEBUG: FEN result keys before return: {list(fen_result.keys())}")
                logger.info(f"DEBUG: FEN result query_type: {fen_result.get('query_type')}")
                return fen_result
        
        elif query_type == "direct":
            logger.info(f"Direct query type detected: '{query}'. Skipping retrieval and returning empty results.")
            # For direct queries, return empty results since no retrieval is needed
            return {
                "retrieved_chunks": [],
                "stockfish_analysis": [],
                "query_type": "direct"
            }
        elif query_type in ["semantic_search", "general_query", "lesson_query", "explain_concept"]:
            logger.info(f"Dispatching to retrieve_semantic for query: '{query}', context_fen: {fen_for_analysis}, class: {target_class_name}")
            analyze_board_flag = True if fen_for_analysis else False
            semantic_result = self.retrieve_semantic(
                query=query, 
                k=k_results, 
                context_fen=fen_for_analysis, 
                analyze_board=analyze_board_flag,
                class_name=target_class_name
            )
            # Add query_type to the semantic result
            semantic_result["query_type"] = query_type
            return semantic_result
        else:
            logger.warning(f"Unknown query type '{query_type}' or insufficient params. Defaulting to broad semantic search for query: '{query}'")
            fallback_result = self.retrieve_semantic(query=query, k=k_results, context_fen=fen_for_analysis, analyze_board=True if fen_for_analysis else False, class_name="ChessGame")
            # Add query_type to the fallback result
            fallback_result["query_type"] = query_type
            return fallback_result

# Example usage for testing (requires etl.utils and other components to be available)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Running RetrieverAgent standalone test...")

    # Mock Weaviate and StockfishAnalyzer for this test to run without full dependencies
    class MockWeaviateClient:
        def __init__(self):
            logger.info("MockWeaviateClient initialized.")
        # Add mock methods as needed by search_weaviate if it's called directly

    class MockStockfishAnalyzer:
        def __init__(self, stockfish_path):
            self.path = stockfish_path
            logger.info(f"MockStockfishAnalyzer initialized with path: {self.path}")
        def get_stockfish_analysis(self, fen, time_limit_ms=1000):
            logger.info(f"MockStockfishAnalyzer.get_stockfish_analysis called for FEN: {fen}")
            return {"best_move_san": "e4", "score_value": "+0.1", "depth": 10, "fen_analyzed": fen}

    # Mock utility functions if etl.utils is not available during this standalone test
    def mock_query_opening_book_by_fen(book_path, fen, k=3):
        logger.info(f"mock_query_opening_book_by_fen called for FEN: {fen}")
        if fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1":
            return [{"eco": "A00", "name": "Start Position", "moves": ""}]
        return []

    def mock_search_weaviate(client, query, class_name, k, alpha, vector, properties):
        logger.info(f"mock_search_weaviate called for query: {query}, class: {class_name}")
        return [{ "id": "mock_id_1", "content": f"Mock content for {query}", "class": class_name}]

    # Replace actual utilities with mocks for the test
    query_opening_book_by_fen = mock_query_opening_book_by_fen
    search_weaviate = mock_search_weaviate

    try:
        mock_client = MockWeaviateClient()
        # Use a dummy path for Stockfish in mock
        mock_sf_analyzer = MockStockfishAnalyzer(stockfish_path=etl_config_module.STOCKFISH_PATH) 

        retriever = RetrieverAgent(
            client=mock_client,
            opening_book_path=etl_config_module.OPENING_BOOK_PATH,
        )

        test_fen_opening = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        opening_results = retriever.retrieve(query="", metadata={"query_type": "opening_lookup", "fen_for_analysis": test_fen_opening})
        logger.info(f"Opening lookup results:\n{json.dumps(opening_results, indent=2)}")

        test_query_semantic = "Queen's Gambit Declined games"
        test_fen_semantic = "rnbqkb1r/pp2pp1p/3p1np1/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6"
        semantic_results = retriever.retrieve(
            query=test_query_semantic, 
            metadata={"query_type": "semantic_search", "fen_for_analysis": test_fen_semantic, "target_class_name": "ChessGame"}
        )
        logger.info(f"Semantic search results:\n{json.dumps(semantic_results, indent=2)}")
        
        general_query = "best continuations in this position"
        general_fen = "r1bqkbnr/pp1ppppp/2n5/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
        general_results = retriever.retrieve(query=general_query, metadata={"query_type": "general_query", "fen_for_analysis": general_fen})
        logger.info(f"General query results:\n{json.dumps(general_results, indent=2)}")

    except Exception as e:
        logger.error(f"Error during RetrieverAgent standalone test: {e}", exc_info=True)
    finally:
        logger.info("RetrieverAgent standalone test finished.") 