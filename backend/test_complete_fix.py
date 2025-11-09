#!/usr/bin/env python3

import requests
import json

def test_complete_fix():
    """Test the complete fix for the Answer Agent issue."""
    
    print("🧪 Testing Complete Fix: Answer Agent Issue")
    print("=" * 60)
    
    api_url = "http://localhost:5001/api/chat/rag"
    
    test_cases = [
        {
            "name": "Simple Math Question (should be direct)",
            "query": "What is 2+2?",
            "expected_query_type": "direct",
            "expected_sources": 0
        },
        {
            "name": "Calculate Question (should be direct)",
            "query": "Calculate 5 + 5",
            "expected_query_type": "direct", 
            "expected_sources": 0
        },
        {
            "name": "Greeting (should be direct)",
            "query": "Hello, how are you?",
            "expected_query_type": "direct",
            "expected_sources": 0
        },
        {
            "name": "Chess Question (should use retrieval)",
            "query": "Find games by Magnus Carlsen",
            "expected_query_type": "game_search",
            "expected_sources": ">0"
        },
        {
            "name": "Chess Opening Question (should use retrieval)",
            "query": "What opening is this position?",
            "expected_query_type": "opening_lookup",
            "expected_sources": ">0"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Query: '{test_case['query']}'")
        
        try:
            response = requests.post(api_url, json={
                'query': test_case['query'],
                'session_id': f'test_fix_{i}',
                'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                query_type = result.get('query_type', 'unknown')
                sources_count = len(result.get('sources', []))
                answer = result.get('answer', 'No answer')
                
                print(f"   ✅ Query type: {query_type}")
                print(f"   ✅ Sources: {sources_count}")
                print(f"   ✅ Answer: {answer[:80]}...")
                
                # Check expectations
                if query_type == test_case['expected_query_type']:
                    print(f"   ✅ Query type matches expected: {test_case['expected_query_type']}")
                else:
                    print(f"   ❌ Query type mismatch! Expected: {test_case['expected_query_type']}, Got: {query_type}")
                
                if test_case['expected_sources'] == 0:
                    if sources_count == 0:
                        print(f"   ✅ Sources count matches expected: 0")
                    else:
                        print(f"   ❌ Sources count mismatch! Expected: 0, Got: {sources_count}")
                elif test_case['expected_sources'] == ">0":
                    if sources_count > 0:
                        print(f"   ✅ Sources count matches expected: >0")
                    else:
                        print(f"   ❌ Sources count mismatch! Expected: >0, Got: {sources_count}")
                
                # Check if answer contains chess game information (should not for direct queries)
                chess_indicators = ["Retrieved Information:", "🎮 Games Found:", "Event:", "ECO:", "View Game"]
                has_chess_info = any(indicator in answer for indicator in chess_indicators)
                
                if test_case['expected_sources'] == 0:
                    if not has_chess_info:
                        print(f"   ✅ Answer does not contain chess game information")
                    else:
                        print(f"   ❌ Answer contains unwanted chess game information!")
                        print(f"       Chess indicators found: {[ind for ind in chess_indicators if ind in answer]}")
                
            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"       Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    print(f"\n{'='*60}")
    print("Test completed!")

if __name__ == "__main__":
    test_complete_fix() 