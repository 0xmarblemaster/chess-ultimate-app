#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.agents.retriever_agent import retrieve_by_fen

def test_current_fen():
    """Test FEN search with the current problematic FEN"""
    
    # This is the FEN from the logs that's causing issues
    test_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3"
    
    print(f"Testing problematic FEN: {test_fen}")
    
    results = retrieve_by_fen(test_fen, limit=3)
    print(f"Number of results: {len(results)}")
    
    for i, result in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        if isinstance(result, dict):
            print(f"Type: {result.get('type')}")
            print(f"Keys: {list(result.keys())}")
            if result.get('message'):
                print(f"Message: {result.get('message')}")
            if result.get('game_id'):
                print(f"Game ID: {result.get('game_id')}")
            if result.get('source'):
                print(f"Source: {result.get('source')}")
        else:
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")

if __name__ == "__main__":
    test_current_fen() 