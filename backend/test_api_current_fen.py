#!/usr/bin/env python3

import requests
import json

def test_api_current_fen_fix():
    """Test the API with the exact scenario that was failing in the logs."""
    
    print("Testing API Current FEN Fix...")
    print("=" * 60)
    
    # Simulate the exact scenario from the logs
    api_url = "http://localhost:5001/api/chat/rag"
    
    # Test case 1: User asks about "current FEN" but query contains different FEN
    test_data = {
        "query": "Search games for the current FEN r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3",
        "session_id": "test_session_123",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position (current board)
        "query_type": "semantic_search"
    }
    
    print(f"Test Case 1: User asks about 'current FEN'")
    print(f"Query: {test_data['query']}")
    print(f"Current board FEN (from UI): {test_data['fen']}")
    print(f"FEN in query text: r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3")
    print()
    
    try:
        response = requests.post(api_url, json=test_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✓ API Response Status: {response.status_code}")
            print(f"✓ Query Type: {result.get('query_type')}")
            print(f"✓ FEN used for search: {result.get('fen')}")
            print(f"✓ Number of sources: {len(result.get('sources', []))}")
            
            # Check if the answer mentions the correct position
            answer = result.get('answer', '')
            print(f"✓ Answer length: {len(answer)} characters")
            
            # Verify the fix worked - should use current board FEN, not query FEN
            expected_fen = test_data['fen']  # Starting position
            actual_fen = result.get('fen')
            
            if actual_fen == expected_fen:
                print(f"✅ SUCCESS: API correctly used current board FEN: {actual_fen}")
                print(f"✅ The system now properly understands 'current FEN' refers to the UI board!")
            else:
                print(f"❌ FAILED: API used wrong FEN")
                print(f"   Expected (current board): {expected_fen}")
                print(f"   Actual: {actual_fen}")
                return False
                
            # Show a preview of the answer
            print(f"\\nAnswer preview:")
            print("-" * 40)
            print(answer[:200] + "..." if len(answer) > 200 else answer)
            print("-" * 40)
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    print()
    
    # Test case 2: User asks about specific FEN (should use query FEN)
    print("Test Case 2: User asks about specific FEN (not current)")
    test_data2 = {
        "query": "Find games with FEN r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3",
        "session_id": "test_session_456",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position (current board)
        "query_type": "semantic_search"
    }
    
    print(f"Query: {test_data2['query']}")
    print(f"Current board FEN: {test_data2['fen']}")
    print()
    
    try:
        response2 = requests.post(api_url, json=test_data2, timeout=30)
        
        if response2.status_code == 200:
            result2 = response2.json()
            
            print(f"✓ API Response Status: {response2.status_code}")
            print(f"✓ Query Type: {result2.get('query_type')}")
            print(f"✓ FEN used for search: {result2.get('fen')}")
            
            # This should use the FEN from the query, not current board
            expected_fen2 = "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3"
            actual_fen2 = result2.get('fen')
            
            if actual_fen2 == expected_fen2:
                print(f"✅ SUCCESS: API correctly used query FEN for specific search: {actual_fen2}")
            else:
                print(f"❌ FAILED: API used wrong FEN for specific search")
                print(f"   Expected (query FEN): {expected_fen2}")
                print(f"   Actual: {actual_fen2}")
                return False
                
        else:
            print(f"❌ API Error: {response2.status_code}")
            print(f"Response: {response2.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    print()
    print("🎉 All API tests passed! Current FEN fix is working correctly in the live system!")
    return True

if __name__ == "__main__":
    test_api_current_fen_fix() 