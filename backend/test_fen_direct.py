#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_fen_direct_debug():
    """Test retrieve_by_fen with debug output"""
    try:
        from backend.etl.agents.retriever_agent import retrieve_by_fen, normalize_fen_for_matching
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
        
        test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        normalized_test = normalize_fen_for_matching(test_fen)
        
        print(f"=== Direct FEN Test ===")
        print(f"Test FEN: {test_fen}")
        print(f"Normalized: {normalized_test}")
        
        # Let's manually check the database first
        print(f"\n=== Manual Database Check ===")
        client = get_weaviate_client()
        collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
        results = collection.query.fetch_objects(limit=50)
        
        expected_exact_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        found_match = False
        
        for obj in results.objects:
            props = obj.properties
            fen = props.get('fen', '')
            name = props.get('opening_name', '')
            
            # Check for exact match
            if fen == expected_exact_fen:
                print(f"✅ Found exact match: {name}")
                print(f"   FEN: {fen}")
                found_match = True
                break
                
            # Check for normalized match  
            if fen and normalize_fen_for_matching(fen) == normalized_test:
                print(f"✅ Found normalized match: {name}")
                print(f"   FEN: {fen}")
                print(f"   Normalized: {normalize_fen_for_matching(fen)}")
                found_match = True
                break
        
        if not found_match:
            print("❌ No manual match found!")
            
        # client.close() removed - Weaviate client manages connections automatically
        
        # Now test the retrieve_by_fen function
        print(f"\n=== Testing retrieve_by_fen function ===")
        results = retrieve_by_fen(test_fen, limit=3)
        print(f"Results count: {len(results)}")
        
        for i, result in enumerate(results):
            print(f"{i+1}. {result}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fen_direct_debug() 