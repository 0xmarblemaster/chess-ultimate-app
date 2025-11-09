#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.agents.retriever_agent import retrieve_by_fen

def test_fen_result_types():
    """Test what types of results FEN search returns"""
    
    test_fen = "rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 4"
    
    print(f"Testing FEN: {test_fen}")
    
    results = retrieve_by_fen(test_fen, limit=3)
    print(f"Number of results: {len(results)}")
    
    for i, result in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        if isinstance(result, dict):
            print(f"Type: {result.get('type')}")
            print(f"Keys: {list(result.keys())}")
            print(f"Source: {result.get('source')}")
            print(f"Game ID: {result.get('game_id')}")
        else:
            print(f"Not a dict: {type(result)}")

if __name__ == "__main__":
    test_fen_result_types() 