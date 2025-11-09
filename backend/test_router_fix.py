#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

from backend.etl.agents.router_agent import RouterAgent

def test_router_fix():
    router = RouterAgent()
    
    test_cases = [
        {
            'query': 'Show me games with this position',
            'fen': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
            'expected': 'game_search'
        },
        {
            'query': 'Find games in this position',
            'fen': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
            'expected': 'game_search'
        },
        {
            'query': 'What is the best move here?',
            'fen': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
            'expected': 'semantic'
        }
    ]
    
    print("=== Testing Router Fix ===")
    for i, test_case in enumerate(test_cases, 1):
        test_state = {
            'user_query': test_case['query'],
            'current_board_fen': test_case['fen'],
            'router_metadata': {}
        }
        
        result = router.classify_query(test_state)
        query_type = result.get('query_type')
        fen_for_analysis = result.get('fen_for_analysis')
        
        print(f"\\nTest {i}:")
        print(f"  Query: '{test_case['query']}'")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Got: {query_type}")
        print(f"  FEN for Analysis: {fen_for_analysis}")
        print(f"  ✅ PASS" if query_type == test_case['expected'] else f"  ❌ FAIL")

if __name__ == "__main__":
    test_router_fix() 