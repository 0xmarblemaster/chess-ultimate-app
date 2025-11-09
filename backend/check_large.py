#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def check_large():
    """Check more database records"""
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
        
        expected_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        
        client = get_weaviate_client()
        collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
        results = collection.query.fetch_objects(limit=500)
        
        print(f"Checking {len(results.objects)} openings for match...")
        match_found = False
        
        for i, obj in enumerate(results.objects):
            props = obj.properties
            fen = props.get('fen', '')
            if fen == expected_fen:
                print(f"✅ Match at index {i}: {props.get('opening_name', 'N/A')}")
                print(f"   ECO: {props.get('eco_code', 'N/A')}")
                print(f"   Moves: {props.get('san_moves', 'N/A')}")
                match_found = True
                break
        
        if not match_found:
            print("❌ No match found in 500 results")
        
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_large() 