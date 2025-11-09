import weaviate
from typing import Dict, List, Optional, Any

from .. import config as etl_config # To get Weaviate URL and API key if needed
from . import opening_agent # Re-use get_weaviate_client from opening_agent for consistency

CHESS_GAME_COLLECTION_NAME = getattr(etl_config, 'WEAVIATE_GAMES_CLASS_NAME', "ChessGame")

# Define the properties to return for game searches
# These should match the properties defined in games_loader.py schema
GAME_RETURN_PROPERTIES = [
    "white_player", "black_player", "event", "site", "round", "date_utc", 
    "result", "eco", "opening_name", "ply_count", "final_fen", "mid_game_fen",
    "pgn_moves", "source_file", "white_elo", "black_elo", "event_date",
    "white_title", "black_title", "white_fide_id", "black_fide_id", "all_ply_fens"
]

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

def find_games_by_criteria(
    filters: Optional[Dict[str, Any]] = None,
    fen_to_match: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Searches the ChessGame collection in Weaviate based on various criteria.

    Args:
        filters: A dictionary of filter criteria. 
                 Supported keys: "white_player", "black_player", "eco", "event".
        fen_to_match: A specific FEN string to match against 'final_fen' or 'mid_game_fen'.
        limit: Maximum number of games to return.

    Returns:
        A list of game data dictionaries, or an empty list if no games are found or an error occurs.
    """
    client = opening_agent.get_weaviate_client() # Re-use client logic
    if not client:
        print("ERROR: [GameSearchAgent] Could not connect to Weaviate.")
        return [{"error": "Could not connect to Weaviate for game search."}]

    game_results = []
    weaviate_filters_list = []

    try:
        # Use v3 syntax for getting collection
        games_collection_name = CHESS_GAME_COLLECTION_NAME

        # Build filters from the filters dictionary using v3 syntax
        if filters:
            player_filters = []
            if "white_player" in filters and filters["white_player"]:
                player_filters.append({
                    "path": ["white_player"],
                    "operator": "Like",
                    "valueText": f"*{filters['white_player']}*"
                })
            if "black_player" in filters and filters["black_player"]:
                player_filters.append({
                    "path": ["black_player"],
                    "operator": "Like",
                    "valueText": f"*{filters['black_player']}*"
                })
            
            # Handle any_player filter - search both white_player and black_player
            if "any_player" in filters and filters["any_player"]:
                any_player_filter = {
                    "operator": "Or",
                    "operands": [
                        {
                            "path": ["white_player"],
                            "operator": "Like",
                            "valueText": f"*{filters['any_player']}*"
                        },
                        {
                            "path": ["black_player"],
                            "operator": "Like",
                            "valueText": f"*{filters['any_player']}*"
                        }
                    ]
                }
                player_filters.append(any_player_filter)
            
            # If both player filters are present, they should be ANDed together
            if len(player_filters) == 2:
                weaviate_filters_list.append({
                    "operator": "And",
                    "operands": player_filters
                })
            elif len(player_filters) == 1:
                weaviate_filters_list.append(player_filters[0])

            if "eco" in filters and filters["eco"]:
                # ECO codes can be broad (e.g., "B") or specific (e.g., "B22")
                weaviate_filters_list.append({
                    "path": ["eco"],
                    "operator": "Like",
                    "valueText": f"*{filters['eco']}*"
                })
            
            if "event" in filters and filters["event"]:
                weaviate_filters_list.append({
                    "path": ["event"],
                    "operator": "Like",
                    "valueText": f"*{filters['event']}*"
                })
        
        # Add FEN filter if provided (searches with multiple strategies)
        if fen_to_match:
            normalized_fen = normalize_fen_for_matching(fen_to_match)
            print(f"DEBUG: [GameSearchAgent] Searching for FEN: {fen_to_match}")
            print(f"DEBUG: [GameSearchAgent] Normalized FEN: {normalized_fen}")
            
            # Strategy 1: Exact FEN match using v3 syntax
            fen_filter_operands = [
                {
                    "path": ["final_fen"],
                    "operator": "Equal",
                    "valueText": fen_to_match
                },
                {
                    "path": ["mid_game_fen"],
                    "operator": "Equal",
                    "valueText": fen_to_match
                },
                # CRITICAL: Search in all_ply_fens array - this is where most positions exist!
                {
                    "path": ["all_ply_fens"],
                    "operator": "ContainsAny",
                    "valueText": [fen_to_match]
                }
            ]
            
            # Add normalized matches if different from original
            if normalized_fen != fen_to_match:
                fen_filter_operands.extend([
                    {
                        "path": ["final_fen"],
                        "operator": "Equal",
                        "valueText": normalized_fen
                    },
                    {
                        "path": ["mid_game_fen"],
                        "operator": "Equal",
                        "valueText": normalized_fen
                    },
                    # Also search normalized FEN in all_ply_fens
                    {
                        "path": ["all_ply_fens"],
                        "operator": "ContainsAny",
                        "valueText": [normalized_fen]
                    }
                ])
            
            fen_filter = {
                "operator": "Or",
                "operands": fen_filter_operands
            }
            weaviate_filters_list.append(fen_filter)

        # Combine all top-level filters with AND
        final_filter_condition = None
        if len(weaviate_filters_list) > 1:
            final_filter_condition = {
                "operator": "And",
                "operands": weaviate_filters_list
            }
        elif len(weaviate_filters_list) == 1:
            final_filter_condition = weaviate_filters_list[0]
        
        print(f"DEBUG: [GameSearchAgent] Number of filters in list: {len(weaviate_filters_list)}")
        print(f"DEBUG: [GameSearchAgent] Final filter condition: {final_filter_condition}")
        print(f"DEBUG: [GameSearchAgent] FEN provided: {fen_to_match is not None}")
        print(f"DEBUG: [GameSearchAgent] Player filters provided: {filters is not None}")

        # CRITICAL: If we have no filters at all, return no results instead of all games
        if final_filter_condition is None and not fen_to_match:
            print("DEBUG: [GameSearchAgent] No filters provided - returning no results")
            return [{"message": "No search criteria provided."}]

        # Use v3 query syntax
        query_params = {
            "limit": limit,
            "properties": GAME_RETURN_PROPERTIES
        }
        
        if final_filter_condition:
            query_params["where"] = final_filter_condition

        response = client.query.get(games_collection_name, GAME_RETURN_PROPERTIES).with_additional(["id"]).with_limit(limit)
        
        if final_filter_condition:
            response = response.with_where(final_filter_condition)
        
        result = response.do()

        print(f"DEBUG: [GameSearchAgent] Weaviate response: {result}")

        # Process v3 response format
        if result and result.get("data") and result["data"].get("Get") and result["data"]["Get"].get(games_collection_name):
            games = result["data"]["Get"][games_collection_name]
            for game_data in games:
                # Add UUID from additional data
                if "_additional" in game_data and "id" in game_data["_additional"]:
                    game_data["uuid"] = game_data["_additional"]["id"]
                game_data["type"] = "chess_game_search_result" # For AnswerAgent formatting
                game_results.append(game_data)
            print(f"DEBUG: [GameSearchAgent] Found {len(game_results)} games matching criteria.")
            
            # ADDITIONAL DEBUG: If we searched by FEN, check if any results actually contain the FEN
            if fen_to_match:
                fen_matches = 0
                for game in game_results:
                    final_fen = game.get('final_fen', '')
                    mid_fen = game.get('mid_game_fen', '') 
                    all_fens = game.get('all_ply_fens', [])
                    
                    if (final_fen == fen_to_match or 
                        mid_fen == fen_to_match or 
                        (isinstance(all_fens, list) and fen_to_match in all_fens)):
                        fen_matches += 1
                
                print(f"DEBUG: [GameSearchAgent] FEN exact matches: {fen_matches}/{len(game_results)}")
                
                if fen_matches == 0:
                    print(f"WARNING: [GameSearchAgent] No games actually contain the searched FEN position!")
                    print(f"WARNING: [GameSearchAgent] This suggests the FEN filter is not working correctly")
                    # Return no results if FEN search found games but none actually contain the FEN
                    return [{"message": f"No games found containing the position: {fen_to_match}"}]
        else:
            print("DEBUG: [GameSearchAgent] No games found matching the criteria.")
            # Return a specific message if no results, rather than just empty list
            # This helps distinguish no results from an error later.
            return [{"message": "No games found matching your criteria."}]

    except Exception as e:
        print(f"ERROR: [GameSearchAgent] Error querying Weaviate for games: {e}")
        # Ensure a consistent error format
        return [{"error": f"Error querying game database: {str(e)}"}]
    finally:
        if client:
            pass  # # client.close() removed - Weaviate client manages connections automatically removed - newer Weaviate client manages connections automatically

    return game_results

if __name__ == '__main__':
    # Example Usage (requires Weaviate to be running and populated)
    print("Testing GameSearchAgent...")
    
    # Test 1: Search by player
    # print("\n--- Test 1: Search by White Player 'Carlsen' ---")
    # carlsen_games = find_games_by_criteria(filters={"white_player": "Carlsen"}, limit=3)
    # for game in carlsen_games:
    #     print(f"  Event: {game.get('event')}, White: {game.get('white_player')}, Black: {game.get('black_player')}, Result: {game.get('result')}")
    #     # print(f"    Moves: {game.get('pgn_moves')[:50]}...") # Print first 50 chars of moves

    # Test 2: Search by ECO code
    # print("\n--- Test 2: Search by ECO 'C' (Sicilian, Caro-Kann, French etc.) ---")
    # eco_c_games = find_games_by_criteria(filters={"eco": "C"}, limit=2)
    # for game in eco_c_games:
    #     print(f"  Event: {game.get('event')}, ECO: {game.get('eco')}, White: {game.get('white_player')}, Black: {game.get('black_player')}")

    # Test 3: Search by a specific FEN (replace with a FEN from your DB)
    # print("\n--- Test 3: Search by FEN (example FEN) ---")
    # example_fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2" # King's Pawn Game after 1.e4 e5
    # fen_games = find_games_by_criteria(fen_to_match=example_fen, limit=2)
    # for game in fen_games:
    #      print(f"  Event: {game.get('event')}, Matched FEN: {example_fen} (in final_fen or mid_game_fen)")
    #      print(f"    Final FEN in DB: {game.get('final_fen')}")
    #      print(f"    Mid FEN in DB: {game.get('mid_game_fen')}")

    # Test 4: Combined filter
    # print("\n--- Test 4: Search by Black Player 'Anand' and ECO starts with 'D' ---")
    # combined_games = find_games_by_criteria(filters={"black_player": "Anand", "eco": "D"}, limit=3)
    # for game in combined_games:
    #     print(f"  Event: {game.get('event')}, ECO: {game.get('eco')}, White: {game.get('white_player')}, Black: {game.get('black_player')}")

    # Test 5: No results expected (or specific query known to have no results)
    # print("\n--- Test 5: Search for non-existent player ---")
    # no_results_games = find_games_by_criteria(filters={"white_player": "NonExistentPlayer123"})
    # if no_results_games and no_results_games[0].get("message"):
    #     print(f"  Result: {no_results_games[0]["message"]}")
    # elif no_results_games:
    #      print(f"  Found unexpected games: {len(no_results_games)}")

    print("\nGameSearchAgent testing complete. Uncomment tests to run.") 