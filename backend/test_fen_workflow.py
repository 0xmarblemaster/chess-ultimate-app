#!/usr/bin/env python3

import requests
import json
from etl.weaviate_loader import get_weaviate_client
from weaviate.collections.classes.filters import Filter

def test_fen_workflow():
    """Test the complete FEN search workflow from user request to results."""
    
    # Test FENs
    test_fens = [
        # FEN that we know works
        "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3",
        # Starting position
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        # After 1.e4
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        # After 1.e4 e5
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
    ]
    
    print("=== Testing FEN Search Workflow ===\n")
    
    for i, test_fen in enumerate(test_fens, 1):
        print(f"Test {i}: {test_fen}")
        
        # Step 1: Direct database search
        print("  Step 1: Direct database search...")
        client = get_weaviate_client()
        if client:
            try:
                games_collection = client.collections.get('ChessGame')
                response = games_collection.query.fetch_objects(
                    filters=Filter.by_property("all_ply_fens").contains_any([test_fen]),
                    limit=10
                )
                db_count = len(response.objects) if response.objects else 0
                print(f"    Database found: {db_count} games")
                
                if db_count > 0:
                    # Show first game details
                    first_game = response.objects[0]
                    props = first_game.properties
                    print(f"    First game: {props.get('white_player')} vs {props.get('black_player')}")
                    print(f"    UUID: {str(first_game.uuid)}")
                
            except Exception as e:
                print(f"    Database error: {e}")
            finally:
                # client.close() removed - Weaviate client manages connections automatically
        
        # Step 2: API call
        print("  Step 2: API call...")
        try:
            payload = {
                "query": f"Search games for the current FEN {test_fen}",
                "fen": test_fen,
                "session_id": f"test-workflow-{i}"
            }
            
            response = requests.post(
                "http://localhost:5001/api/chat/rag",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                api_count = len(data.get('sources', []))
                print(f"    API found: {api_count} sources")
                
                # Check if sources have game_id
                game_sources = [s for s in data.get('sources', []) if s.get('type') == 'chess_game_search_result']
                print(f"    Game sources: {len(game_sources)}")
                
                if game_sources:
                    print(f"    First game ID: {game_sources[0].get('game_id', 'MISSING')}")
                
                # Check answer quality
                answer = data.get('answer', '')
                has_game_id = 'Game ID:' in answer or any(s.get('game_id') for s in game_sources)
                print(f"    Answer includes Game ID: {has_game_id}")
                
            else:
                print(f"    API error: {response.status_code}")
                
        except Exception as e:
            print(f"    API call error: {e}")
        
        print()

def test_specific_failing_fen():
    """Test a FEN that the user mentioned was failing."""
    print("=== Testing User-Reported Failing FEN ===\n")
    
    # Let's try some common positions that might be failing
    failing_fens = [
        # Sicilian Defense
        "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
        # French Defense
        "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        # Caro-Kann Defense
        "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    ]
    
    for fen in failing_fens:
        print(f"Testing: {fen}")
        
        # Direct database check
        client = get_weaviate_client()
        if client:
            try:
                games_collection = client.collections.get('ChessGame')
                response = games_collection.query.fetch_objects(
                    filters=Filter.by_property("all_ply_fens").contains_any([fen]),
                    limit=5
                )
                count = len(response.objects) if response.objects else 0
                print(f"  Database: {count} games found")
                
                if count > 0:
                    # Test API
                    payload = {
                        "query": f"Find games with this position {fen}",
                        "fen": fen,
                        "session_id": "test-failing"
                    }
                    
                    response = requests.post(
                        "http://localhost:5001/api/chat/rag",
                        headers={"Content-Type": "application/json"},
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        api_sources = len(data.get('sources', []))
                        print(f"  API: {api_sources} sources returned")
                        
                        answer = data.get('answer', '')
                        if 'Game ID:' in answer:
                            print("  ✅ Answer includes Game ID")
                        else:
                            print("  ❌ Answer missing Game ID")
                    else:
                        print(f"  API error: {response.status_code}")
                
            except Exception as e:
                print(f"  Error: {e}")
            finally:
                # client.close() removed - Weaviate client manages connections automatically
        
        print()

if __name__ == '__main__':
    test_fen_workflow()
    test_specific_failing_fen() 