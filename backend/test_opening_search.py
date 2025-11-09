#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def test_opening_search():
    """Test searching for e4 openings"""
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
        
        client = get_weaviate_client()
        if not client:
            print("❌ Failed to connect to Weaviate")
            return
            
        print("✅ Connected to Weaviate")
        
        # Search for e4 openings
        print(f"\n=== Searching for e4 openings in {CHESS_OPENING_CLASS_NAME} ===")
        try:
            collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
            
            # Search for e4 related openings
            results = collection.query.near_text(
                query="e4 King pawn opening",
                limit=5,
                return_properties=["opening_name", "fen", "eco_code", "san_moves"]
            )
            
            if results and results.objects:
                print(f"Found {len(results.objects)} e4 opening results:")
                for i, obj in enumerate(results.objects):
                    props = obj.properties
                    print(f"  {i+1}. {props.get('opening_name', 'N/A')}")
                    print(f"      ECO: {props.get('eco_code', 'N/A')}")
                    print(f"      FEN: {props.get('fen', 'N/A')}")
                    print(f"      Moves: {props.get('san_moves', 'N/A')}")
                    print()
            else:
                print("❌ No e4 opening results found")
                
            # Also try searching for the exact FEN
            test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
            print(f"\n=== Searching for exact FEN: {test_fen} ===")
            
            # Get all openings and check for FEN matches
            all_results = collection.query.fetch_objects(limit=100)
            matches = []
            
            for obj in all_results.objects:
                props = obj.properties
                if props.get('fen') == test_fen:
                    matches.append(props)
                elif props.get('fen_before_last_move') == test_fen:
                    matches.append(props)
                    
            if matches:
                print(f"Found {len(matches)} exact FEN matches:")
                for match in matches:
                    print(f"  - {match.get('opening_name', 'N/A')} (ECO: {match.get('eco_code', 'N/A')})")
            else:
                print("❌ No exact FEN matches found")
                
        except Exception as e:
            print(f"❌ Error searching openings: {e}")
            
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_opening_search() 