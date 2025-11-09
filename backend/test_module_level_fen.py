#!/usr/bin/env python3

import sys
sys.path.append('/home/marblemaster/Desktop/Cursor/mvp1/backend')

from etl.agents.retriever_agent import retrieve_by_fen

# Test the specific FEN
target_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"

print(f"=== TESTING MODULE-LEVEL retrieve_by_fen ===")
print(f"Target FEN: {target_fen}")

try:
    results = retrieve_by_fen(target_fen, limit=5)
    
    print(f"\nResults: {len(results)} items found")
    
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Type: {result.get('type', 'unknown')}")
        if result.get('type') == 'chess_game_search_result':
            print(f"  Game ID: {result.get('game_id', 'N/A')}")
            print(f"  Players: {result.get('white_player', 'N/A')} vs {result.get('black_player', 'N/A')}")
            print(f"  Event: {result.get('event', 'N/A')}")
            print(f"  ECO: {result.get('eco', 'N/A')}")
            print(f"  Opening: {result.get('opening', 'N/A')}")
            print(f"  Result: {result.get('result', 'N/A')}")
            print(f"  Score: {result.get('score', 'N/A')}")
        else:
            print(f"  Content: {str(result)[:200]}...")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 