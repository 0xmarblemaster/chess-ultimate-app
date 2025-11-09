#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_semantic_vs_raw():
    """Compare semantic search vs raw fetch"""
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
        
        expected_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        
        client = get_weaviate_client()
        collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
        
        print("=== SEMANTIC SEARCH (near_text) ===")
        semantic_results = collection.query.near_text(
            query="e4 King pawn opening",
            limit=10,
            return_properties=["opening_name", "fen", "eco_code", "san_moves"]
        )
        
        print(f"Found {len(semantic_results.objects)} semantic results:")
        semantic_match = False
        for i, obj in enumerate(semantic_results.objects):
            props = obj.properties
            fen = props.get('fen', '')
            name = props.get('opening_name', '')
            print(f"  {i+1}. {name}")
            print(f"      FEN: {fen}")
            
            if fen == expected_fen:
                print(f"      *** SEMANTIC MATCH! ***")
                semantic_match = True
        
        print(f"\n=== RAW FETCH (fetch_objects) ===")
        raw_results = collection.query.fetch_objects(
            limit=100,
            return_properties=["opening_name", "fen", "eco_code", "san_moves"]
        )
        
        print(f"Found {len(raw_results.objects)} raw results:")
        raw_match = False
        for i, obj in enumerate(raw_results.objects):
            props = obj.properties
            fen = props.get('fen', '')
            name = props.get('opening_name', '')
            
            if fen == expected_fen:
                print(f"  {i+1}. {name} - *** RAW MATCH! ***")
                print(f"      FEN: {fen}")
                raw_match = True
        
        print(f"\n=== SUMMARY ===")
        print(f"Semantic search found match: {semantic_match}")
        print(f"Raw fetch found match: {raw_match}")
        
        # If semantic found it but raw didn't, this suggests the data exists
        # but might be ordered differently or have different indexing
        
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_semantic_vs_raw() 