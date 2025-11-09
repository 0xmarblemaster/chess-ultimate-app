#!/usr/bin/env python3

import requests
import json
import time

def test_api_direct():
    """Test the API directly with a simple math question."""
    
    print("🧪 Testing API Direct Call")
    print("=" * 50)
    
    api_url = "http://localhost:5001/api/chat/rag"
    
    test_data = {
        'query': 'What is 2+2?',
        'session_id': 'test_direct_api',
        'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    }
    
    print(f"Sending request to: {api_url}")
    print(f"Request data: {json.dumps(test_data, indent=2)}")
    print()
    
    try:
        response = requests.post(api_url, json=test_data, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("Response data:")
            print(f"  Query type: {result.get('query_type')}")
            print(f"  Sources count: {len(result.get('sources', []))}")
            print(f"  Answer: {result.get('answer', 'No answer')[:100]}...")
            print(f"  Metadata: {result.get('metadata', {})}")
            
            # Check if the response contains chess game information
            answer = result.get('answer', '')
            chess_indicators = ["Retrieved Information:", "🎮 Games Found:", "Event:", "ECO:", "View Game"]
            has_chess_info = any(indicator in answer for indicator in chess_indicators)
            print(f"  Contains chess info: {has_chess_info}")
            
            # Print full response for debugging
            print("\nFull response:")
            print(json.dumps(result, indent=2))
            
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api_direct() 