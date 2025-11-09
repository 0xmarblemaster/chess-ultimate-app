#!/usr/bin/env python3
"""
Test to identify TWIC loading issues
"""

import weaviate
import chess
import chess.pgn
from pathlib import Path

def get_weaviate_client():
    """Get Weaviate client."""
    openai_key = "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"
    
    headers = {}
    if openai_key:
        headers["X-OpenAI-Api-Key"] = openai_key
    
    try:
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True
        )
        print("✅ Connected to Weaviate successfully")
        return client
    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {e}")
        return None

def test_simple_insert():
    """Test inserting a single game."""
    print("\n🧪 Testing simple game insertion...")
    
    client = get_weaviate_client()
    if not client:
        return
    
    try:
        collection = client.collections.get("ChessGame")
        
        # Count before
        count_before = collection.aggregate.over_all(total_count=True).total_count
        print(f"Games before insert: {count_before}")
        
        # Test data
        test_game = {
            "white_player": "Test Player 1",
            "black_player": "Test Player 2",
            "event": "Test Event",
            "site": "Test Site",
            "round": "1",
            "result": "1-0",
            "date": "2025.06.01",
            "source_file": "test.pgn",
            "moves": "1. e4 e5 2. Nf3 Nc6 3. Bb5 1-0",
            "starting_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "ending_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "move_count": 3
        }
        
        # Try to insert
        print("Attempting to insert test game...")
        result = collection.data.insert(test_game)
        print(f"Insert result: {result}")
        
        # Count after
        count_after = collection.aggregate.over_all(total_count=True).total_count
        print(f"Games after insert: {count_after}")
        print(f"Games added: {count_after - count_before}")
        
    except Exception as e:
        print(f"❌ Insert test failed: {e}")
    finally:
        # client.close() removed - Weaviate client manages connections automatically

def test_twic_file_parsing():
    """Test parsing a TWIC file."""
    print("\n🧪 Testing TWIC file parsing...")
    
    twic_file = Path("data/twic_pgn/twic_downloads/all_extracted_pgn/twic0920_twic920.pgn")
    
    if not twic_file.exists():
        print(f"❌ Test file not found: {twic_file}")
        return
    
    try:
        with open(twic_file, 'r', encoding='utf-8', errors='ignore') as f:
            game_count = 0
            for i in range(5):  # Test first 5 games
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                
                game_count += 1
                headers = game.headers
                print(f"Game {game_count}: {headers.get('White', 'Unknown')} vs {headers.get('Black', 'Unknown')}")
                print(f"  Event: {headers.get('Event', 'Unknown')}")
                print(f"  ELO: {headers.get('WhiteElo', 'N/A')} vs {headers.get('BlackElo', 'N/A')}")
                
            print(f"✅ Successfully parsed {game_count} games from TWIC file")
            
    except Exception as e:
        print(f"❌ TWIC parsing failed: {e}")

def test_batch_insert():
    """Test batch insertion."""
    print("\n🧪 Testing batch insertion...")
    
    client = get_weaviate_client()
    if not client:
        return
    
    try:
        collection = client.collections.get("ChessGame")
        
        # Count before
        count_before = collection.aggregate.over_all(total_count=True).total_count
        print(f"Games before batch: {count_before}")
        
        # Create test batch
        batch_data = []
        for i in range(3):
            game_data = {
                "white_player": f"Batch Player {i*2+1}",
                "black_player": f"Batch Player {i*2+2}",
                "event": f"Batch Test Event {i}",
                "site": "Batch Test Site",
                "round": str(i+1),
                "result": "1-0" if i % 2 == 0 else "0-1",
                "date": "2025.06.01",
                "source_file": "batch_test.pgn",
                "moves": f"1. e4 e5 2. Nf3 Nc6 {i+3}. Bb5 1-0",
                "starting_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "ending_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "move_count": 3
            }
            batch_data.append(game_data)
        
        # Try batch insert
        print(f"Attempting to insert batch of {len(batch_data)} games...")
        with collection.batch.dynamic() as batch:
            for data in batch_data:
                batch.add_object(properties=data)
        
        print("Batch insert completed")
        
        # Count after
        count_after = collection.aggregate.over_all(total_count=True).total_count
        print(f"Games after batch: {count_after}")
        print(f"Games added: {count_after - count_before}")
        
    except Exception as e:
        print(f"❌ Batch test failed: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
    finally:
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    print("🔍 DIAGNOSING TWIC LOADING ISSUES")
    print("=" * 50)
    
    test_simple_insert()
    test_twic_file_parsing()
    test_batch_insert()
    
    print("\n" + "=" * 50)
    print("🏁 Diagnostic tests complete") 