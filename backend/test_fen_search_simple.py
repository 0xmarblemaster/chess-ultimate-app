#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.weaviate_loader import get_weaviate_client

def test_direct_fen_search():
    # Test FEN that should exist in our database
    test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    
    print(f"Testing direct FEN search for: {test_fen}")
    print("=" * 60)
    
    try:
        client = get_weaviate_client()
        if not client:
            print("ERROR: Could not connect to Weaviate")
            return
            
        print("Connected to Weaviate successfully")
        
        # Get the ChessGame collection
        game_collection = client.collections.get("ChessGame")
        print("Got ChessGame collection")
        
        # Try to find games that contain this FEN
        from weaviate.collections.classes.filters import Filter
        
        print(f"Searching for games containing FEN: {test_fen}")
        
        # Search using contains_any filter
        results = game_collection.query.fetch_objects(
            filters=Filter.by_property("all_ply_fens").contains_any([test_fen]),
            limit=5
        )
        
        if results and results.objects:
            print(f"Found {len(results.objects)} games with exact FEN match:")
            for i, obj in enumerate(results.objects):
                props = obj.properties
                print(f"  Game {i+1}: {props.get('white_player')} vs {props.get('black_player')}")
                print(f"    Event: {props.get('event')}")
                print(f"    UUID: {str(obj.uuid)}")
                
                # Check if our FEN is actually in the all_ply_fens
                all_fens = props.get('all_ply_fens', [])
                if test_fen in all_fens:
                    fen_index = all_fens.index(test_fen)
                    print(f"    FEN found at position {fen_index + 1}")
                else:
                    print(f"    FEN NOT found in all_ply_fens (this is unexpected)")
        else:
            print("No games found with exact FEN match")
            
            # Try a broader search - get first few games and check manually
            print("\nTrying broader search - checking first 10 games manually:")
            broad_results = game_collection.query.fetch_objects(limit=10)
            
            if broad_results and broad_results.objects:
                found_any = False
                for i, obj in enumerate(broad_results.objects):
                    props = obj.properties
                    all_fens = props.get('all_ply_fens', [])
                    if test_fen in all_fens:
                        found_any = True
                        fen_index = all_fens.index(test_fen)
                        print(f"  FOUND in Game {i+1}: {props.get('white_player')} vs {props.get('black_player')}")
                        print(f"    FEN at position {fen_index + 1}")
                        break
                
                if not found_any:
                    print("  FEN not found in first 10 games either")
                    print("  Let's check what the first FEN looks like in the first game:")
                    first_game = broad_results.objects[0]
                    first_fens = first_game.properties.get('all_ply_fens', [])
                    if first_fens:
                        print(f"    First FEN in DB: '{first_fens[0]}'")
                        print(f"    Search FEN:     '{test_fen}'")
                        print(f"    Are they equal? {first_fens[0] == test_fen}")
            else:
                print("No games found in database at all!")
        
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"ERROR during direct FEN search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_fen_search() 