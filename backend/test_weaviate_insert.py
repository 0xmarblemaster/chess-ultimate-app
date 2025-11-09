#!/usr/bin/env python3
"""
Test Weaviate batch insert to understand response format
"""

import sys
sys.path.insert(0, '/home/marblemaster/Desktop/Cursor/mvp1')

from backend.etl.weaviate_loader import get_weaviate_client

def test_batch_insert():
    """Test a small batch insert to understand the response format."""
    
    client = get_weaviate_client()
    if not client:
        print("❌ Could not connect to Weaviate")
        return
    
    collection = client.collections.get("ChessGame")
    
    # Create a small test batch
    test_batch = [
        {
            "white_player": "Test Player 1",
            "black_player": "Test Player 2",
            "event": "Test Event",
            "site": "Test Site",
            "round": "1",
            "result": "1-0",
            "date": "2025.06.02",
            "source_file": "test.pgn",
            "eco": "A00",
            "opening": "Test Opening",
            "event_date": "2025.06.02",
            "moves": "1. e4 e5 2. Nf3 Nc6",
            "move_count": 4.0,
            "starting_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "ending_fen": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            "white_elo": 1500.0,
            "black_elo": 1400.0
        }
    ]
    
    print(f"🧪 Testing batch insert with {len(test_batch)} games")
    
    try:
        response = collection.data.insert_many(test_batch)
        
        print(f"📊 Response type: {type(response)}")
        print(f"📊 Response attributes: {dir(response)}")
        
        # Check different possible attributes
        if hasattr(response, 'objects'):
            print(f"✅ Has 'objects' attribute: {len(response.objects)} items")
            if response.objects:
                print(f"   First object type: {type(response.objects[0])}")
                print(f"   First object attributes: {dir(response.objects[0])}")
        
        if hasattr(response, 'all_responses'):
            print(f"✅ Has 'all_responses' attribute: {len(response.all_responses)} items")
            if response.all_responses:
                print(f"   First response type: {type(response.all_responses[0])}")
                print(f"   First response attributes: {dir(response.all_responses[0])}")
        
        if hasattr(response, 'failed_objects'):
            print(f"✅ Has 'failed_objects' attribute: {response.failed_objects}")
        
        if hasattr(response, 'errors'):
            print(f"✅ Has 'errors' attribute: {response.errors}")
        
        if hasattr(response, 'uuids'):
            print(f"✅ Has 'uuids' attribute: {len(response.uuids) if response.uuids else 0} items")
        
        # Try to determine success/failure
        print("\n🔍 Analyzing success/failure:")
        
        if hasattr(response, 'errors') and hasattr(response, 'uuids'):
            # New format
            total_items = len(test_batch)
            error_count = len(response.errors) if response.errors else 0
            uuid_count = len(response.uuids) if response.uuids else 0
            print(f"   New format: {uuid_count} UUIDs, {error_count} errors out of {total_items} total")
            
            if response.errors:
                print(f"   Sample error: {response.errors[0]}")
        
    except Exception as e:
        print(f"❌ Error during batch insert: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    test_batch_insert() 