#!/usr/bin/env python3
"""Test insertion after Weaviate restart"""

from fixed_twic_loader import get_weaviate_client

def test_insert():
    client = get_weaviate_client()
    if not client:
        return
    
    try:
        collection = client.collections.get("ChessGame")
        
        # Count before
        count_before = collection.aggregate.over_all(total_count=True).total_count
        print(f"Games before insert: {count_before:,}")
        
        # Test game
        test_game = {
            "white_player": "API Test Player 1",
            "black_player": "API Test Player 2",
            "event": "API Test Event",
            "site": "Test Site",
            "round": "1",
            "result": "1-0",
            "date": "2025.06.01",
            "source_file": "api_test.pgn",
            "moves": "1. e4 e5 2. Nf3 1-0",
            "starting_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "ending_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "move_count": 2
        }
        
        # Insert
        print("Inserting test game...")
        result = collection.data.insert(test_game)
        print(f"Insert result: {result}")
        
        # Count after
        count_after = collection.aggregate.over_all(total_count=True).total_count
        print(f"Games after insert: {count_after:,}")
        print(f"✅ Successfully added {count_after - count_before} game(s)!")
        
    except Exception as e:
        print(f"❌ Insert failed: {e}")
    finally:
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    test_insert() 