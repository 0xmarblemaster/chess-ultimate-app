#!/usr/bin/env python3
"""
Fixed retrieve_by_fen function that properly searches ChessGame collection
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional
import re
from etl.weaviate_loader import get_weaviate_client
from etl import config as etl_config_module

# Regex for FEN validation and extraction
FEN_REGEX = re.compile(r'([rnbqkpRNBQKP1-8]+/){7}([rnbqkpRNBQKP1-8]+)\s+(w|b)\s+(-|K?Q?k?q?)\s+(-|[a-h][36])\s+(\d+)\s+(\d+)')

def normalize_fen_for_matching(fen: str) -> str:
    """
    Normalizes a FEN string for better matching by handling en passant variations.
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

def retrieve_by_fen_fixed(fen: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fixed version that works with the actual ChessGame collection schema.
    """
    client = get_weaviate_client()
    if not client:
        return [{"error": "Could not connect to Weaviate database"}]
    
    all_matching_items = []
    normalized_search_fen = normalize_fen_for_matching(fen)

    try:
        # Query ChessGame collection for actual games
        from weaviate.collections.classes.filters import Filter
        game_collection = client.collections.get("ChessGame")
        
        # Strategy A: Direct exact FEN search using Weaviate filtering
        try:
            exact_results = game_collection.query.fetch_objects(
                filters=Filter.by_property("all_ply_fens").contains_any([fen.strip()]),
                limit=limit
            )
            if exact_results and exact_results.objects:
                for obj in exact_results.objects:
                    obj_props = obj.properties
                    all_matching_items.append({
                        "type": "chess_game_search_result",
                        "game_id": str(obj.uuid),
                        "uuid": str(obj.uuid),
                        "white_player": obj_props.get("white_player"),
                        "black_player": obj_props.get("black_player"),
                        "white_elo": obj_props.get("white_elo"),
                        "black_elo": obj_props.get("black_elo"),
                        "event": obj_props.get("event"),
                        "site": obj_props.get("site"),
                        "date_utc": obj_props.get("date_utc"),
                        "round": obj_props.get("round"),
                        "eco": obj_props.get("eco"),
                        "opening": obj_props.get("opening"),  # Use 'opening' not 'opening_name'
                        "result": obj_props.get("result"),
                        "pgn_moves": obj_props.get("pgn_moves"),
                        "final_fen": obj_props.get("final_fen"),
                        "mid_game_fen": obj_props.get("mid_game_fen"),
                        "ply_count": obj_props.get("ply_count"),
                        "matched_fen": fen.strip(),
                        "fen_match_type": "exact",
                        "source": "chess_game",
                        "score": 20
                    })
                print(f"Found {len(exact_results.objects)} games with exact FEN match")
        except Exception as e:
            print(f"Error in exact FEN search: {e}")
        
        # Strategy B: If no exact matches found, try normalized FEN search
        if not all_matching_items:
            try:
                # Get a reasonable sample of games to check for normalized matches
                sample_results = game_collection.query.fetch_objects(limit=100)
                if sample_results and sample_results.objects:
                    for obj in sample_results.objects:
                        obj_props = obj.properties
                        all_ply_fens = obj_props.get('all_ply_fens', [])
                        
                        # Check if any FEN in the game matches our normalized search FEN
                        for game_fen in all_ply_fens:
                            if normalize_fen_for_matching(game_fen) == normalized_search_fen:
                                all_matching_items.append({
                                    "type": "chess_game_search_result",
                                    "game_id": str(obj.uuid),
                                    "uuid": str(obj.uuid),
                                    "white_player": obj_props.get("white_player"),
                                    "black_player": obj_props.get("black_player"),
                                    "white_elo": obj_props.get("white_elo"),
                                    "black_elo": obj_props.get("black_elo"),
                                    "event": obj_props.get("event"),
                                    "site": obj_props.get("site"),
                                    "date_utc": obj_props.get("date_utc"),
                                    "round": obj_props.get("round"),
                                    "eco": obj_props.get("eco"),
                                    "opening": obj_props.get("opening"),
                                    "result": obj_props.get("result"),
                                    "pgn_moves": obj_props.get("pgn_moves"),
                                    "final_fen": obj_props.get("final_fen"),
                                    "mid_game_fen": obj_props.get("mid_game_fen"),
                                    "ply_count": obj_props.get("ply_count"),
                                    "matched_fen": game_fen,
                                    "fen_match_type": "normalized",
                                    "source": "chess_game",
                                    "score": 18
                                })
                                break  # Only need one match per game
                        
                        if len(all_matching_items) >= limit:
                            break
                    
                    if all_matching_items:
                        print(f"Found {len(all_matching_items)} games with normalized FEN match")
            except Exception as e:
                print(f"Error in normalized FEN search: {e}")

        # client.close() removed - Weaviate client manages connections automatically

        if not all_matching_items:
            return [{"message": f"No games found with FEN: {fen}"}]

        # Sort by score (higher score is better)
        all_matching_items.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Return unique items and limit the number of results
        final_results = []
        seen_identifiers = set()

        for item in all_matching_items:
            identifier = item.get("game_id") or item.get("uuid")
            
            if identifier and identifier not in seen_identifiers:
                final_results.append(item)
                seen_identifiers.add(identifier)
            elif not identifier:
                final_results.append(item)

            if len(final_results) >= limit:
                break
        
        return final_results

    except Exception as e:
        if client and hasattr(client, 'close'): 
            # client.close() removed - Weaviate client manages connections automatically
        return [{"error": f"Error querying Weaviate by FEN: {str(e)}"}]

# Test the fixed function
if __name__ == "__main__":
    test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    print(f"Testing FEN search for: {test_fen}")
    results = retrieve_by_fen_fixed(test_fen, limit=3)
    
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        if result.get("error"):
            print(f"  {i+1}. ERROR: {result['error']}")
        elif result.get("message"):
            print(f"  {i+1}. MESSAGE: {result['message']}")
        else:
            print(f"  {i+1}. Game: {result.get('white_player')} vs {result.get('black_player')}")
            print(f"      Event: {result.get('event')}")
            print(f"      UUID: {result.get('uuid')}")
            print(f"      Match type: {result.get('fen_match_type')}") 