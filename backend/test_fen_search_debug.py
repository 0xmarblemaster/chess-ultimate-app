#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.agents.retriever_agent import retrieve_by_fen

def test_fen_search_debug():
    """Test what the FEN search actually returns"""
    
    print("🔍 Testing FEN search debug...")
    
    # Test FEN that should exist in the database
    test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    
    print(f"Searching for FEN: {test_fen}")
    
    try:
        # Call the module-level retrieve_by_fen function directly
        results = retrieve_by_fen(test_fen, limit=5)
        
        print(f"Number of results: {len(results)}")
        
        for i, result in enumerate(results):
            print(f"\n--- Result {i+1} ---")
            print(f"Type: {type(result)}")
            print(f"Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            if isinstance(result, dict):
                print(f"result.get('type'): {result.get('type')}")
                print(f"result.get('source'): {result.get('source')}")
                print(f"result.get('error'): {result.get('error')}")
                print(f"result.get('message'): {result.get('message')}")
                print(f"result.get('data'): {result.get('data') is not None}")
                print(f"result.get('fen'): {result.get('fen') is not None}")
                print(f"result.get('text'): {result.get('text') is not None}")
                print(f"result.get('game_id'): {result.get('game_id')}")
                
                # Check the meaningful results logic
                is_meaningful = False
                if not (result.get("error") or result.get("message")):
                    if (result.get("data") or result.get("fen") or result.get("text") or 
                        result.get("type") == "chess_game_search_result"):
                        is_meaningful = True
                
                print(f"Would be considered meaningful: {is_meaningful}")
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fen_search_debug() 