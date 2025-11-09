#!/usr/bin/env python3
import sys
import os

# Add the mvp1 directory to the path
mvp1_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, mvp1_dir)

from backend.etl.agents.router_agent import RouterAgent

def test_gukesh_query():
    router = RouterAgent()
    
    test_queries = [
        "Gukesh games",
        "games by Gukesh", 
        "find games with Gukesh",
        "show me Gukesh games",
        "search for Gukesh games"
    ]
    
    print("=== Testing Router Classification for Gukesh Queries ===")
    
    for query in test_queries:
        test_state = {
            'user_query': query,
            'current_board_fen': None,
            'router_metadata': {}
        }
        
        result = router.classify_query(test_state)
        
        print(f"\nQuery: '{query}'")
        print(f"  Classified as: {result.get('query_type')}")
        print(f"  Game filters: {result.get('game_filters')}")
        print(f"  FEN for analysis: {result.get('fen_for_analysis')}")

if __name__ == "__main__":
    test_gukesh_query() 