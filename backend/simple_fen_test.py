#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl.agents.retriever_agent import retrieve_by_fen

target_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
print(f"Testing FEN: {target_fen}")

try:
    results = retrieve_by_fen(target_fen, limit=5)
    print(f"Found {len(results)} results")
    
    for i, result in enumerate(results):
        if result.get('type') == 'chess_game_search_result':
            print(f"  Game {i+1}: {result.get('white_player')} vs {result.get('black_player')} - {result.get('eco')}")
        else:
            print(f"  Result {i+1}: {str(result)[:100]}...")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 