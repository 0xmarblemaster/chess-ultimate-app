#!/usr/bin/env python3

import requests
import json

def test_simple_api():
    """Test the API with a simple query to see the exact error."""
    
    print("Testing Simple API Call...")
    print("=" * 40)
    
    api_url = "http://localhost:5001/api/chat/rag"
    
    test_data = {
        "query": "What is 2+2?",
        "session_id": "test_simple",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "query_type": "semantic_search"
    }
    
    print(f"Making API call to: {api_url}")
    print(f"Data: {test_data}")
    
    try:
        response = requests.post(api_url, json=test_data, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Answer: {result.get('answer', 'No answer')}")
            print(f"Query Type: {result.get('query_type', 'Unknown')}")
            
            if "error" in result.get('answer', '').lower():
                print("❌ Error found in answer!")
                return False
            else:
                print("✅ API call successful!")
                return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    test_simple_api() 