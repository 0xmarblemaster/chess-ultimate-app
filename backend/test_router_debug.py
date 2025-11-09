#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_router_classification():
    print("Testing Router Agent Classification...")
    print("=" * 50)
    
    try:
        from etl.agents.router_agent import RouterAgent
        
        router = RouterAgent()
        
        test_queries = [
            "What is 2+2?",
            "Calculate 5 + 5",
            "Hello, how are you?",
            "Explain what chess is",
            "Find games by Magnus Carlsen",
            "What opening is this position?"
        ]
        
        for query in test_queries:
            print(f"\nTesting: '{query}'")
            
            state = {
                'user_query': query,
                'current_board_fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'router_metadata': {}
            }
            
            result = router.classify_query(state)
            print(f"  Query type: {result.get('query_type')}")
            print(f"  Metadata: {result.get('router_metadata')}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_router_classification() 