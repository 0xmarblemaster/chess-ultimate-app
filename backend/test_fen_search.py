#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.agents.retriever_agent import retrieve_by_fen

def test_fen_search():
    # Test FEN that should exist in our database
    test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    
    print(f"Testing FEN search for: {test_fen}")
    print("=" * 60)
    
    try:
        results = retrieve_by_fen(test_fen, limit=5)
        print(f"Found {len(results)} results:")
        
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            if isinstance(result, dict):
                if result.get("error"):
                    print(f"  ERROR: {result['error']}")
                elif result.get("message"):
                    print(f"  MESSAGE: {result['message']}")
                elif result.get("type") == "chess_game_search_result":
                    print(f"  GAME: {result.get('white_player')} vs {result.get('black_player')}")
                    print(f"  EVENT: {result.get('event')}")
                    print(f"  UUID: {result.get('game_id')}")
                    print(f"  MATCH TYPE: {result.get('fen_match_type')}")
                else:
                    print(f"  DATA: {result}")
            else:
                print(f"  RESULT: {result}")
                
    except Exception as e:
        print(f"ERROR during FEN search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fen_search() 