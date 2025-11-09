#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.agents.retriever_agent import retrieve_by_fen

def test_existing_fen():
    """Test FEN search with a position that should exist in the database"""
    
    # Test with 1.c4 position which should exist in the database
    test_fen = "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1"
    
    print(f"Testing FEN that should exist: {test_fen}")
    
    results = retrieve_by_fen(test_fen, limit=3)
    print(f"Number of results: {len(results)}")
    
    for i, result in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        if isinstance(result, dict):
            print(f"Type: {result.get('type')}")
            print(f"Game ID: {result.get('game_id')}")
            print(f"Source: {result.get('source')}")
            if result.get('message'):
                print(f"Message: {result.get('message')}")
        else:
            print(f"Not a dict: {type(result)}")

if __name__ == "__main__":
    test_existing_fen() 