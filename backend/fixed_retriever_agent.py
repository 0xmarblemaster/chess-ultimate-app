#!/usr/bin/env python3

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
    # But normalize en passant to "-" and reset halfmove/fullmove counters
    normalized_parts = parts[:3] + [parts[3], "-", "0", "1"]
    return " ".join(normalized_parts)

def retrieve_by_fen_fixed(fen: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fixed version of retrieve_by_fen that uses correct property names.
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
        # Query ChessGame collection (the only collection that exists)
        from weaviate.collections.classes.filters import Filter
        game_collection = client.collections.get("ChessGame")
        
        # Strategy A: Direct exact FEN search using Weaviate filtering
        try:
            exact_results = game_collection.query.fetch_objects(
                filters=Filter.by_property("all_ply_fens").contains_any([fen]),
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
                        "white_fide_id": obj_props.get("white_fide_id"),
                        "black_fide_id": obj_props.get("black_fide_id"),
                        "event": obj_props.get("event"),
                        "site": obj_props.get("site"),
                        "date_utc": obj_props.get("date_utc"),
                        "round": obj_props.get("round"),
                        "eco": obj_props.get("eco"),
                        "opening": obj_props.get("opening"),  # Fixed: was "opening_name"
                        "result": obj_props.get("result"),
                        "pgn_moves": obj_props.get("pgn_moves"),
                        "final_fen": obj_props.get("final_fen"),
                        "mid_game_fen": obj_props.get("mid_game_fen"),
                        "ply_count": obj_props.get("ply_count"),
                        "moves_san": obj_props.get("moves_san"),  # Fixed: was "san_moves"
                        "moves_uci": obj_props.get("moves_uci"),  # Fixed: was "uci_moves"
                        "matched_fen": fen,
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
                sample_results = game_collection.query.fetch_objects(limit=200)
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
                                    "white_fide_id": obj_props.get("white_fide_id"),
                                    "black_fide_id": obj_props.get("black_fide_id"),
                                    "event": obj_props.get("event"),
                                    "site": obj_props.get("site"),
                                    "date_utc": obj_props.get("date_utc"),
                                    "round": obj_props.get("round"),
                                    "eco": obj_props.get("eco"),
                                    "opening": obj_props.get("opening"),  # Fixed: was "opening_name"
                                    "result": obj_props.get("result"),
                                    "pgn_moves": obj_props.get("pgn_moves"),
                                    "final_fen": obj_props.get("final_fen"),
                                    "mid_game_fen": obj_props.get("mid_game_fen"),
                                    "ply_count": obj_props.get("ply_count"),
                                    "moves_san": obj_props.get("moves_san"),  # Fixed: was "san_moves"
                                    "moves_uci": obj_props.get("moves_uci"),  # Fixed: was "uci_moves"
                                    "matched_fen": game_fen,
                                    "fen_match_type": "normalized",
                                    "source": "chess_game",
                                    "score": 15
                                })
                                break  # Only add each game once
                        
                        if len(all_matching_items) >= limit:
                            break
                            
                print(f"Found {len(all_matching_items)} games with normalized FEN match")
            except Exception as e:
                print(f"Error in normalized FEN search: {e}")
                
    except Exception as e:
        print(f"Error querying ChessGame collection: {e}")
    finally:
        if client:
            # client.close() removed - Weaviate client manages connections automatically
    
    # Sort by score (highest first) and return top results
    all_matching_items.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_matching_items[:limit]

def test_fixed_retriever():
    """Test the fixed retriever function"""
    print("Testing fixed retriever function...")
    
    # Test FEN from the workflow
    test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    print(f"Searching for FEN: {test_fen}")
    
    results = retrieve_by_fen_fixed(test_fen, limit=3)
    
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Game ID: {result.get('game_id')}")
        print(f"  White: {result.get('white_player')}")
        print(f"  Black: {result.get('black_player')}")
        print(f"  Event: {result.get('event')}")
        print(f"  Opening: {result.get('opening')}")
        print(f"  ECO: {result.get('eco')}")
        print(f"  Match Type: {result.get('fen_match_type')}")
        print(f"  Score: {result.get('score')}")

if __name__ == "__main__":
    test_fixed_retriever() 