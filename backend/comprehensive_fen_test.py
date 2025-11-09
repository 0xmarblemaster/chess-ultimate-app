#!/usr/bin/env python3

import sys
import requests
import json
sys.path.insert(0, '/home/marblemaster/Desktop/Cursor/mvp1')

def test_fen_via_api(fen, description):
    """Test FEN search via the API"""
    print(f"\n🔍 Testing {description}")
    print(f"FEN: {fen}")
    
    try:
        payload = {
            "query": f"Search games for this FEN {fen}",
            "session_id": "comprehensive_test",
            "fen": fen
        }
        
        response = requests.post(
            "http://localhost:5001/api/chat/rag",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            sources_count = len(data.get("sources", []))
            query_type = data.get("query_type", "unknown")
            
            print(f"✅ API Response: {response.status_code}")
            print(f"   Query Type: {query_type}")
            print(f"   Sources Found: {sources_count}")
            
            if sources_count > 0:
                print(f"   First Source: {data['sources'][0].get('type', 'unknown')} - {data['sources'][0].get('white_player', 'Unknown')} vs {data['sources'][0].get('black_player', 'Unknown')}")
            else:
                answer_snippet = data.get("answer", "No answer")[:100] + "..."
                print(f"   Answer: {answer_snippet}")
            
            return sources_count > 0
        else:
            print(f"❌ API Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_fen_direct(fen, description):
    """Test FEN search directly via game search agent"""
    print(f"\n🎯 Direct Test {description}")
    
    try:
        from backend.etl.agents.game_search_agent import find_games_by_criteria
        
        results = find_games_by_criteria(fen_to_match=fen, limit=3)
        
        if results:
            if isinstance(results[0], dict) and results[0].get('error'):
                print(f"❌ Error: {results[0]['error']}")
                return False
            elif isinstance(results[0], dict) and results[0].get('message'):
                print(f"ℹ️  Message: {results[0]['message']}")
                return False
            else:
                print(f"✅ Direct: Found {len(results)} games")
                if len(results) > 0 and 'white_player' in results[0]:
                    print(f"   First Game: {results[0].get('white_player')} vs {results[0].get('black_player')}")
                return True
        else:
            print(f"❌ Direct: No results")
            return False
            
    except Exception as e:
        print(f"❌ Direct Exception: {e}")
        return False

def main():
    print("🏁 COMPREHENSIVE FEN SEARCH TEST")
    print("=" * 50)
    
    test_cases = [
        # Starting position - should exist in most games
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Starting Position"),
        
        # After 1.e4 - very common
        ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", "After 1.e4"),
        
        # User's first FEN
        ("r1bqk1nr/pppp1ppp/2n5/2b5/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5", "User's First FEN"),
        
        # User's second FEN  
        ("r1bqk1nr/pppp1ppp/2n5/2b5/3NP3/4B3/PPP2PPP/RN1QKB1R b KQkq - 2 5", "User's Second FEN")
    ]
    
    for fen, description in test_cases:
        # Test both direct and API approaches
        direct_success = test_fen_direct(fen, description)
        api_success = test_fen_via_api(fen, description)
        
        print(f"   🎯 Direct: {'✅' if direct_success else '❌'}")
        print(f"   🌐 API: {'✅' if api_success else '❌'}")
        print("-" * 30)
    
    print("\n📊 Test Summary:")
    print("If the starting position and 1.e4 work, the fix is successful!")
    print("If user's specific FENs don't work, those positions might not exist in the database.")

if __name__ == "__main__":
    main() 