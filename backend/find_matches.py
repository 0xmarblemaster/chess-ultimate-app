#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

def find_matches():
    """Find FEN matches in the database"""
    try:
        from backend.etl.weaviate_loader import get_weaviate_client
        from backend.etl.openings_loader import CLASS_NAME as CHESS_OPENING_CLASS_NAME
        from backend.etl.agents.retriever_agent import normalize_fen_for_matching
        
        test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        normalized_test = normalize_fen_for_matching(test_fen)
        
        client = get_weaviate_client()
        collection = client.collections.get(CHESS_OPENING_CLASS_NAME)
        all_results = collection.query.fetch_objects(limit=300)
        
        print(f"Searching for normalized FEN: {normalized_test}")
        matches = []
        
        for obj in all_results.objects:
            props = obj.properties
            fen = props.get('fen', '')
            if fen and normalize_fen_for_matching(fen) == normalized_test:
                matches.append(props)
        
        print(f"Found {len(matches)} matches:")
        for match in matches:
            print(f"  - {match.get('opening_name', 'N/A')} (ECO: {match.get('eco_code', 'N/A')})")
            print(f"    FEN: {match.get('fen', 'N/A')}")
            print(f"    Moves: {match.get('san_moves', 'N/A')}")
            print()
        
        if not matches:
            print("❌ No matches found. Let's check similar FENs:")
            target_start = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
            for obj in all_results.objects:
                props = obj.properties
                fen = props.get('fen', '')
                if fen.startswith(target_start):
                    print(f"  Similar: {props.get('opening_name', 'N/A')}")
                    print(f"    FEN: {fen}")
                    print(f"    Normalized: {normalize_fen_for_matching(fen)}")
                    print()
        
        # client.close() removed - Weaviate client manages connections automatically
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_matches() 